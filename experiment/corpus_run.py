#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paper-A corpus-level run (P2-A.1).

Non-circular ground truth (KEY):
  VALID  = golden  +  semantics-preserving variants (reformat / consistent
           internal alpha-rename)  +  arbiter's algorithmically-distinct correct
           solutions.  ==> valid BY CONSTRUCTION, independent of the grader.
  BUGGY  = provided buggy_rtl  +  arbiter's broken solutions.
           ==> buggy BY PROVENANCE, independent of the grader.

Graders compared on the SAME independent ground truth:
  PROP      (proposed)  : run the per-objective property TB (invariant assertions).
  TEXT-SIM  (baseline)  : token-Jaccard vs golden, ACCEPT iff sim >= THRESH.
  STRUCT-SIM(baseline)  : identifier-abstracted token-sequence ratio vs golden.

Headline:
  - FNR  = reject-rate on VALID-by-construction  (lower is fairer)
  - FPR  = accept-rate on BUGGY-by-provenance    (lower is safer)
  - FNR is reported separately on NON-golden valid alternatives (variants +
    arbiter alternatives), the population reference-matching is known to harm.

CPU-only (iverilog/vvp). Self-contained in edu_pivot. Touches nothing else.
"""
import json, subprocess, os, re, difflib, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "_corpus_run")
os.makedirs(WORK, exist_ok=True)
TEXT_THRESH = 0.80     # similarity graders accept near-duplicates
STRUCT_THRESH = 0.80
N_RENAME_VARIANTS = 2

VERILOG_KW = set("""module endmodule input output inout wire reg logic integer genvar parameter localparam
assign always initial begin end if else case endcase default for while posedge negedge or and not xor
nand nor xnor buf signed unsigned function endfunction task endtask generate endgenerate automatic
casez casex repeat forever wait disable fork join real time""".split())

class _Hang:                       # sentinel for a process that timed out (hung simulation)
    returncode = 124; stdout = ""; stderr = "TIMEOUT"
def sh(cmd, cwd, timeout=20):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return _Hang()             # zero-delay loop / non-advancing clock -> treat as failure

def compile_run(files, top, tag):
    d = os.path.join(WORK, tag); os.makedirs(d, exist_ok=True)
    names = []
    for n, c in files.items():
        open(os.path.join(d, n), "w").write(c); names.append(n)
    c = sh(["iverilog", "-g2012", "-s", top, "-o", "sim.vvp"] + names, d, timeout=20)
    if c.returncode != 0:
        return None, "COMPILE_ERROR"
    r = sh(["vvp", "sim.vvp"], d, timeout=8)       # hung sim -> _Hang (rc=124) -> no usable output
    if r.returncode != 0:
        return None, "RUNTIME_HANG"
    return r.stdout, None

FAIL_TOK = re.compile(r"\bFAIL|VIOLATION|MISMATCH|GLITCH|TIMEOUT|STARV")
def tb_top(property_tb):
    m = re.search(r"\bmodule\s+(\w+)", property_tb)   # TB top = first module in the TB file
    return m.group(1) if m else "tb"
def prop_grade(rtl, property_tb, tag):
    out, err = compile_run({"dut.v": rtl, "ptb.v": property_tb}, tb_top(property_tb), tag)
    if err:
        return "REJECT", "COMPILE_ERROR"   # uncompilable = reject
    passed = ("PASS" in out) and not FAIL_TOK.search(out)
    return ("ACCEPT" if passed else "REJECT"), (out.strip().splitlines() or [""])[-1][:70]

# ---------- semantics-preserving variant generators ----------
def strip_comments(s):
    s = re.sub(r"//[^\n]*", "", s)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return s

def variant_reformat(rtl):
    s = strip_comments(rtl)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return "// reformatted variant (comments stripped, whitespace normalized)\n" + s.strip() + "\n"

def get_ports_params(rtl):
    names = set()
    m = re.search(r"module\s+\w+\s*(#\s*\([^)]*\))?\s*\((.*?)\);", rtl, flags=re.S)
    if m:
        body = m.group(2)
        for w in re.findall(r"[A-Za-z_]\w*", body):
            names.add(w)
    for w in re.findall(r"\b(?:parameter|localparam)\s+(?:\[[^\]]*\]\s*)?(\w+)", rtl):
        names.add(w)
    return names

def variant_rename(rtl, salt, tb=""):
    """Consistently rename ONLY provably-internal declared signals.
    Bulletproof: exclude ports/params (anything the TB references by name),
    keywords, and stop decl capture at '=' so RHS/system-funcs never leak in."""
    tb_idents = {t for t in _TOK.findall(strip_comments(tb)) if is_ident(t)}
    protect = get_ports_params(rtl) | VERILOG_KW | tb_idents
    decl = set()
    for m in re.finditer(r"\b(?:reg|wire|logic|integer|genvar)\b\s*(?:signed\s*)?(?:\[[^\]]*\]\s*)?([^;=]+)", rtl):
        for tok in _TOK.findall(m.group(1)):          # number-aware + stop at '='
            if re.match(r"[A-Za-z_]\w*$", tok):
                decl.add(tok)
    targets = sorted(n for n in decl if n not in protect)
    if not targets:
        return None
    out = rtl
    for n in targets:                                 # (?<![$']) never touch system-funcs / number bases
        out = re.sub(r"(?<![$'])\b" + re.escape(n) + r"\b", n + "_" + salt, out)
    return "// internal-signal alpha-renamed variant\n" + out

# ---------- REF-OUT baseline: generic differential testing vs golden ----------
def parse_ports(interface):
    """Return [(dir, is_vector, name)] from an interface/module header string."""
    s = re.sub(r"#\s*\([^)]*\)", "", interface, count=1)     # drop param block
    m = re.search(r"\((.*)\)\s*;", s, flags=re.S)
    if not m:
        return []
    ports = []
    for chunk in m.group(1).split(","):
        pm = re.search(r"\b(input|output|inout)\b\s*(?:wire|reg|logic)?\s*(signed\s*)?(\[[^\]]*\])?\s*(\w+)", chunk)
        if pm:
            ports.append((pm.group(1), bool(pm.group(3)), pm.group(4)))
    return ports

def gen_ref_tb(modname, ports, seed="64'h1234_5678_9ABC_DEF1", ncyc=64):
    clks  = [n for d, v, n in ports if d == "input" and re.search(r"cl(oc)?k", n, re.I)]
    rsts  = [n for d, v, n in ports if d == "input" and re.search(r"rst|reset", n, re.I)]
    ins   = [(v, n) for d, v, n in ports if d == "input" and n not in clks and n not in rsts]
    outs  = [(v, n) for d, v, n in ports if d == "output"]
    if not outs:
        return None
    L = []
    L.append("`timescale 1ns/1ps\nmodule tb;")
    for n in clks: L.append(f"  reg {n}=0;")
    for n in rsts: L.append(f"  reg {n}=0;")
    for v, n in ins:  L.append(f"  reg {'[63:0] ' if v else ''}{n}=0;")
    for v, n in outs: L.append(f"  wire {'[63:0] ' if v else ''}{n};")
    L.append("  integer cyc; reg [63:0] lfsr;")
    conns = ", ".join(f".{n}({n})" for d, v, n in ports)
    L.append(f"  {modname} dut({conns});")
    primary = clks[0] if clks else None
    for i, n in enumerate(clks):
        L.append(f"  always #{5 + 2*i} {n} = ~{n};")     # distinct periods per clock
    def assert_rst(active): return [f"    {n} = {'0' if n.endswith('_n') or 'rst_n' in n else '1'} ;" if active
                                    else f"    {n} = {'1' if n.endswith('_n') or 'rst_n' in n else '0'} ;" for n in rsts]
    L.append("  initial begin")
    L.append(f"    lfsr = {seed};")
    L += assert_rst(True)
    for v, n in ins: L.append(f"    {n} = 0;")
    if primary:
        L.append(f"    repeat(4) @(posedge {primary});")
    else:
        L.append("    #20;")
    L += assert_rst(False)
    L.append(f"    for (cyc=0; cyc<{ncyc}; cyc=cyc+1) begin")
    for v, n in ins:
        L.append(f"      lfsr = {{lfsr[62:0], lfsr[63]^lfsr[62]^lfsr[60]^lfsr[59]}};")
        L.append(f"      {n} = lfsr{'[0]' if not v else ''};")
    if primary:
        L.append(f"      @(posedge {primary}); #1;")
    else:
        L.append("      #10;")
    disp = " ".join(f"{n}=%h" for v, n in outs)
    args = ", ".join(n for v, n in outs)
    L.append(f'      $display("C%0d {disp}", cyc, {args});')
    L.append("    end")
    L.append("    $finish;")
    L.append("  end")
    L.append("  initial begin #500000; $display(\"TIMEOUT\"); $finish; end")
    L.append("endmodule")
    return "\n".join(L)

def ref_trace(rtl, ref_tb, tag):
    out, err = compile_run({"dut.v": rtl, "rtb.v": ref_tb}, "tb", tag)
    if err:
        return None
    lines = [l for l in out.splitlines() if l.startswith("C")]
    return lines or None

# ---------- controlled bug injection (mutation testing, bug_catalog-aligned) ----------
def _sub_first(rtl, pat, repl):
    m = re.search(pat, rtl)
    return rtl[:m.start()] + repl + rtl[m.end():] if m else None

def inj_blocking_in_ff(rtl):                       # nonblocking -> blocking inside an ff block
    m = re.search(r"always\s*@\s*\(\s*posedge", rtl)
    if not m: return None
    i = rtl.find("<=", m.end())
    return rtl[:i] + " = " + rtl[i+2:] if i >= 0 else None

def inj_arith(rtl):  return _sub_first(rtl, r"(?<![<>=!])\+(?![+=])", "-")   # + -> -
def inj_logic(rtl):  return _sub_first(rtl, r"\|\|", "&&")                    # || -> &&
def inj_rel(rtl):    return _sub_first(rtl, r"(?<![<>=!])>(?![>=])", "<")     # > -> <
def inj_constp1(rtl):                                                         # bump a sized literal
    m = re.search(r"('[sSdDhHbBoO])([0-9a-fA-F]+)", rtl)
    if not m: return None
    try: val = int(m.group(2), 16)
    except: return None
    return rtl[:m.start(2)] + format(val + 1, "x") + rtl[m.end(2):]

INJECTORS = [("blocking_in_ff", inj_blocking_in_ff), ("arith_+to-", inj_arith),
             ("logic_||to&&", inj_logic), ("rel_>to<", inj_rel), ("const_+1", inj_constp1)]

ORACLE_SEEDS = ["64'hDEAD_BEEF_0123_4567", "64'hF00D_FACE_8BAD_F00D"]
ORACLE_NCYC = 128
def oracle_golden(modname, ports, name):
    """Precompute golden's oracle traces once per objective (cached, reused for all mutants)."""
    tbs = [gen_ref_tb(modname, ports, s, ORACLE_NCYC) for s in ORACLE_SEEDS]
    if not all(tbs):
        return None, None
    gts = [ref_trace(golden_cache[name], tb, f"{name}_og{k}") for k, tb in enumerate(tbs)]
    if any(g is None for g in gts):
        return None, None
    return tbs, gts
def mutant_is_buggy(cand, tbs, gts, tagbase):
    """True if mutant diverges from golden on any cached oracle seed (independent of PROP)."""
    for k, tb in enumerate(tbs):
        ct = ref_trace(cand, tb, f"{tagbase}_m{k}")
        if ct is None or ct != gts[k]:
            return True
    return False
golden_cache = {}

# ---------- similarity baselines ----------
_TOK = re.compile(r"""
    \d+'[sS]?[bBoOdDhH][0-9a-fA-FxXzZ?_]+   # sized based literal  4'b0, 8'hFF
  | '[sS]?[bBoOdDhH][0-9a-fA-FxXzZ?_]+      # unsized based literal 'b0
  | \d[\d_]*(?:\.\d+)?                       # plain / real number
  | [A-Za-z_]\w*                            # identifier / keyword
  | [^\s\w]                                 # symbol
""", re.X)
def tokenize(rtl):
    return _TOK.findall(strip_comments(rtl))

def text_sim(a, b):
    A, B = set(tokenize(a)), set(tokenize(b))
    return len(A & B) / max(1, len(A | B))

def abstract(toks):
    return ["ID" if re.match(r"[A-Za-z_]\w*$", t) and t not in VERILOG_KW else t for t in toks]

def struct_sim(a, b):
    return difflib.SequenceMatcher(None, abstract(tokenize(a)), abstract(tokenize(b))).ratio()

def is_ident(t):
    return bool(re.match(r"[A-Za-z_]\w*$", t)) and t not in VERILOG_KW

def is_alpha_equiv(golden, variant):
    """PROP-INDEPENDENT proof of semantics preservation: variant == golden under a
    consistent identifier bijection, with every non-identifier token identical."""
    g, v = tokenize(golden), tokenize(variant)
    if len(g) != len(v):
        return False
    fwd, bwd = {}, {}
    for a, b in zip(g, v):
        if is_ident(a) and is_ident(b):
            if fwd.setdefault(a, b) != b or bwd.setdefault(b, a) != a:
                return False
        elif a != b:
            return False
    return True

# ---------- build corpus ----------
def load_tasks():
    """Merge hard_tasks + pool_tasks (both independently authored by the KASE pipeline),
    dedupe by golden_rtl content, give each a unique display name."""
    tasks = list(json.load(open(os.path.join(HERE, "hard_tasks.json"))))
    pool = os.path.join(HERE, "pool_tasks.json")
    if os.path.exists(pool):
        tasks += list(json.load(open(pool)))
    out, seen_gold, seen_name = [], set(), {}
    for t in tasks:
        g = t.get("golden_rtl", "")
        if not (g and t.get("property_tb") and t.get("buggy_rtl")):
            continue
        if g in seen_gold:                       # same objective already included
            continue
        seen_gold.add(g)
        nm = t["name"]
        seen_name[nm] = seen_name.get(nm, 0) + 1
        t = dict(t, name=nm if seen_name[nm] == 1 else f"{nm}#{seen_name[nm]}")
        out.append(t)
    return out

CACHE = os.path.join(HERE, "corpus_cache.json")
def build_corpus():
    if os.path.exists(CACHE):                      # slow injection oracle runs once; reuse on reruns
        objs = json.load(open(CACHE))
        for o in objs:                             # JSON turns tuples into lists; restore (src,rtl) pairs
            o["valids"] = [tuple(x) for x in o["valids"]]
            o["buggys"] = [tuple(x) for x in o["buggys"]]
        return objs
    objs = _build_corpus_fresh()
    json.dump(objs, open(CACHE, "w"), ensure_ascii=False)
    return objs

def _build_corpus_fresh():
    tasks = load_tasks()
    objs = []
    for t in tasks:
        golden = t["golden_rtl"]; ptb = t["property_tb"]
        valids = [("golden", golden)]
        # only keep generated variants that are PROVABLY semantics-preserving (alpha-equiv to golden)
        rf = variant_reformat(golden)
        if is_alpha_equiv(golden, rf):
            valids.append(("variant_reformat", rf))
        for i in range(N_RENAME_VARIANTS):
            v = variant_rename(golden, f"r{i}", tb=ptb)
            if v and is_alpha_equiv(golden, v):
                valids.append((f"variant_rename{i}", v))
        buggys = [("provided_bug", t["buggy_rtl"])]
        mod = re.search(r"module\s+(\w+)", golden).group(1)
        ports = parse_ports(t["interface"])
        # controlled bug injection — ONLY on deterministic objectives (differential oracle valid).
        # skip arbiter-like (output-multiplicity): a mutant differing from golden may still be valid.
        if not re.search(r"arb|arbit", t["name"], re.I):
            golden_cache[t["name"]] = golden
            tbs, gts = oracle_golden(mod, ports, t["name"])   # golden oracle traces cached once
            if tbs:
                for opname, fn in INJECTORS:
                    mut = fn(golden)
                    if mut and mutant_is_buggy(mut, tbs, gts, f"{t['name']}_{opname}"):
                        buggys.append((f"inj_{opname}", mut))
        objs.append(dict(name=t["name"], golden=golden, ptb=ptb, interface=t["interface"],
                         modname=mod, valids=valids, buggys=buggys, kind="functional"))
    # arbiter objective from arb_bundle (algorithmically diverse correct)
    arb = json.load(open(os.path.join(HERE, "arb_bundle.json")))
    arb_golden = arb["correct"][0]["rtl"]
    arb_hdr = re.search(r"module.*?\);", arb_golden, flags=re.S).group(0)
    objs.append(dict(
        name="rr_arbiter", golden=arb_golden, ptb=arb["property_tb"], interface=arb_hdr,
        modname=re.search(r"module\s+(\w+)", arb_golden).group(1),
        valids=[(f"alt_{c['name']}", c["rtl"]) for c in arb["correct"]],
        buggys=[(b["name"], b["rtl"]) for b in arb["broken"]],
        kind="output-multiplicity"))
    return objs

def main():
    import sys
    objs = build_corpus()
    print(f"[build_corpus done] {len(objs)} objectives", file=sys.stderr, flush=True)
    rows = []
    refout_cov = 0
    for oi, o in enumerate(objs):
        print(f"  grading [{oi+1}/{len(objs)}] {o['name']}", file=sys.stderr, flush=True)
        golden = o["golden"]; ptb = o["ptb"]
        # REF-OUT: build generic differential harness, get golden trace (limited fixed stimulus)
        ref_tb = gen_ref_tb(o["modname"], parse_ports(o["interface"]))
        golden_trace = ref_trace(golden, ref_tb, f"{o['name']}__REFGOLD") if ref_tb else None
        if golden_trace is not None:
            refout_cov += 1
        cands = [("VALID", src, rtl) for src, rtl in o["valids"]] + \
                [("BUGGY", src, rtl) for src, rtl in o["buggys"]]
        for truth, src, rtl in cands:
            tag = f"{o['name']}__{src}".replace("/", "_")[:60]
            pv, pmsg = prop_grade(rtl, ptb, tag)
            ts = text_sim(rtl, golden); ss = struct_sim(rtl, golden)
            # REF-OUT verdict (N/A if golden harness didn't elaborate)
            if golden_trace is None:
                ref_v = "NA"
            else:
                ct = ref_trace(rtl, ref_tb, tag + "_REF")
                ref_v = "ACCEPT" if (ct is not None and ct == golden_trace) else "REJECT"
            rows.append(dict(obj=o["name"], kind=o["kind"], truth=truth, src=src,
                             prop=pv, textsim=ts, structsim=ss, refout=ref_v,
                             text_v="ACCEPT" if ts >= TEXT_THRESH else "REJECT",
                             struct_v="ACCEPT" if ss >= STRUCT_THRESH else "REJECT",
                             is_golden=(src == "golden")))
    # ---- per-objective PROP sanity (should accept all VALID, reject all BUGGY) ----
    print("=" * 100)
    print("PAPER-A CORPUS RUN — property grading vs similarity baselines on construction-based ground truth")
    print("=" * 100)
    nobj = len(objs)
    nvalid = sum(1 for r in rows if r["truth"] == "VALID")
    nbuggy = sum(1 for r in rows if r["truth"] == "BUGGY")
    nalt = sum(1 for r in rows if r["truth"] == "VALID" and not r["is_golden"])
    print(f"objectives={nobj}  submissions={len(rows)}  (VALID={nvalid} [alt={nalt}], BUGGY={nbuggy})\n")

    def metrics(graderkey):
        rr = [r for r in rows if r[graderkey] != "NA"]                 # NA-aware (REF-OUT coverage)
        V  = [r for r in rr if r["truth"] == "VALID"]
        B  = [r for r in rr if r["truth"] == "BUGGY"]
        A  = [r for r in V if not r["is_golden"]]
        fn = sum(1 for r in V if r[graderkey] == "REJECT")
        fp = sum(1 for r in B if r[graderkey] == "ACCEPT")
        fn_alt = sum(1 for r in A if r[graderkey] == "REJECT")
        return dict(fn=fn, fp=fp, fn_alt=fn_alt, nV=len(V), nB=len(B), nA=len(A))

    print(f"objectives={nobj}  submissions={len(rows)}  REF-OUT auto-harness coverage={refout_cov}/{nobj} objectives\n")
    print(f"{'grader':12} | {'FNR (reject valid)':22} {'FPR (accept buggy)':22} {'FNR on alternatives':20}")
    print("-" * 100)
    for key, label in [("prop", "PROP"), ("refout", "REF-OUT"), ("text_v", "TEXT-SIM"), ("struct_v", "STRUCT-SIM")]:
        m = metrics(key)
        fnr = m['fn'] / max(1, m['nV']); fpr = m['fp'] / max(1, m['nB']); fnra = m['fn_alt'] / max(1, m['nA'])
        print(f"{label:12} | {m['fn']:>2}/{m['nV']:<3} = {fnr:.2f}          "
              f"{m['fp']:>2}/{m['nB']:<3} = {fpr:.2f}          "
              f"{m['fn_alt']:>2}/{m['nA']:<3} = {fnra:.2f}")
    print("-" * 100)

    # similarity distribution: do valid-alternatives overlap with buggy? (parameter-free killer)
    alt_ts = [r["textsim"] for r in rows if r["truth"] == "VALID" and not r["is_golden"]]
    bug_ts = [r["textsim"] for r in rows if r["truth"] == "BUGGY"]
    alt_ss = [r["structsim"] for r in rows if r["truth"] == "VALID" and not r["is_golden"]]
    bug_ss = [r["structsim"] for r in rows if r["truth"] == "BUGGY"]
    def stat(x): return f"min={min(x):.2f} med={statistics.median(x):.2f} max={max(x):.2f}" if x else "-"
    print("similarity-to-golden distribution (parameter-free overlap argument):")
    print(f"  TEXT-SIM   valid-alternatives: {stat(alt_ts)}   |   buggy: {stat(bug_ts)}")
    print(f"  STRUCT-SIM valid-alternatives: {stat(alt_ss)}   |   buggy: {stat(bug_ss)}")
    print("  -> if valid-alt range overlaps buggy range, NO threshold separates them: similarity is unfit as a grader.")
    print("=" * 100)

    # PROP failures (where property grader disagrees with construction label -> investigate / expert-study items)
    prop_fn = [r for r in rows if r["truth"] == "VALID" and r["prop"] == "REJECT"]
    prop_fp = [r for r in rows if r["truth"] == "BUGGY" and r["prop"] == "ACCEPT"]
    print(f"PROP disagreements w/ construction GT (expert-study candidates): "
          f"{len(prop_fn)} valid-rejected, {len(prop_fp)} buggy-accepted")
    for r in prop_fn[:12]:
        print(f"   [valid->REJECT] {r['obj']:18} {r['src']}")
    for r in prop_fp[:12]:
        print(f"   [buggy->ACCEPT] {r['obj']:18} {r['src']}")

    json.dump(rows, open(os.path.join(HERE, "corpus_results.json"), "w"), ensure_ascii=False, indent=1)
    print("\nsaved corpus_results.json")

if __name__ == "__main__":
    main()
