#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inferential statistics for the manuscript (CAEAI standards):
Wilson 95% CIs on all proportions; exact McNemar tests for the paired
three-arm gate comparison (same 70 items); Fisher exact for grader FPR/FNR
contrasts; two-pass agreement. Stdlib only; runs locally."""
import json, math, sys
sys.path.insert(0, ".")

def wilson(k, n, z=1.959964):
    if n == 0: return (0.0, 0.0)
    p = k / n
    d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (max(0.0, c-h), min(1.0, c+h))

def mcnemar_exact(b, c):
    """two-sided exact binomial test on discordant pairs"""
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k+1)) * (0.5 ** n)
    return min(1.0, 2 * tail)

def fisher_exact(a, b, c, d):
    """two-sided Fisher for 2x2 [[a,b],[c,d]] via hypergeometric point-prob rule"""
    r1, r2, c1, n = a+b, c+d, a+c, a+b+c+d
    def pmf(x): return math.comb(r1, x) * math.comb(r2, c1-x) / math.comb(n, c1)
    p0 = pmf(a)
    lo, hi = max(0, c1-r2), min(r1, c1)
    return sum(pmf(x) for x in range(lo, hi+1) if pmf(x) <= p0 * (1+1e-9))

def fmt(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k/n:.3f} [95% CI {lo:.3f}, {hi:.3f}]"

out = {}
print("="*88)
print("SECTION A — Wilson 95% CIs for all headline proportions")
print("="*88)
props = {
 "backbone_coverage (sound decisions)": (212, 221),
 "backbone_accuracy (of sound verdicts)": (211, 212),
 "backbone_escalation": (9, 221),
 "grader PROP FNR(valid)": (0, 137), "grader PROP FNR(alternatives)": (0, 101), "grader PROP FPR(buggy)": (9, 84),
 "grader REF-OUT FNR": (1, 137), "grader REF-OUT FPR": (11, 84),
 "grader TEXT-SIM FNR": (17, 137), "grader TEXT-SIM FPR": (82, 84),
 "grader STRUCT-SIM FNR": (2, 137), "grader STRUCT-SIM FPR": (81, 84),
 "gate interception harmful (35+35+6)": (76, 76),
 "gate pass behavior-preserving": (28, 29),
 "gate deliver authentic tutor": (34, 35),
 "scaffold checkpoints valid": (36, 36),
 "scaffold final-step contract": (12, 12),
 "diagnosis actionable": (66, 75),
 "3arm EXEC catch broken": (41, 41), "3arm EXEC pass valid": (28, 29),
 "3arm FRONTIER catch broken": (41, 41), "3arm FRONTIER pass valid": (29, 29),
 "3arm DEEPSEEK catch broken": (36, 41), "3arm DEEPSEEK pass valid": (11, 29),
}
for name, (k, n) in props.items():
    s = fmt(k, n); out[name] = s; print(f"  {name:44} {s}")

print()
print("="*88)
print("SECTION B — Paired McNemar (same 70 items): per-item verdicts")
print("="*88)
# execution-gate per-item verdicts on the EXACT RTL sent to all judges (cq_*.json)
import corpus_run as C
import trustgrade as TG
cache = {o["name"]: o for o in json.load(open("corpus_cache.json"))}
truth = {m["id"]: m for m in json.load(open("critique_truth.json"))}
items = []
for i in range(3):
    items += json.load(open(f"critique_batches/cq_{i}.json"))
exec_v = {}
for it in items:
    obj = cache[truth[it["id"]]["obj"]]
    a = TG.assess(it["proposed_fix_rtl"], obj)
    exec_v[it["id"]] = "APPROVE" if (a["verdict"]=="ACCEPT" and a["backing"].startswith("sound")) else "REJECT"
# DeepSeek verdicts
ds = {r["id"]: r["verdict"] for r in json.load(open("ds_verdicts_deepseek_chat.json"))["verdicts"]}
# frontier verdicts: reparse from the three v2 agent outputs
import html, re
def last_array(fp):
    txt=None
    for line in open(fp):
        try: o=json.loads(line)
        except: continue
        m=o.get("message",{})
        if m.get("role")=="assistant":
            c=m.get("content"); s=""
            if isinstance(c,str): s=c
            elif isinstance(c,list):
                for b in c:
                    if isinstance(b,dict) and b.get("type")=="text": s+=b.get("text","")
            if '"verdict"' in s: txt=s
    starts=[m.start() for m in re.finditer(r'\[\s*\{\s*"id"', txt)]
    raw=txt[starts[-1]:txt.rfind("]")+1]
    for cand in (raw, html.unescape(raw)):
        try: return json.loads(cand)
        except: pass
T="/private/tmp/claude-501/-Users-chenyuanlong/2e0da6f1-ae7f-4fbe-b6b5-dc0fa270c65f/tasks"
fr = {}
for f in ["af2e5b307ced75a4a","a70ffcc67a41ff73d","a204d78469f694aab"]:
    for r in last_array(f"{T}/{f}.output"): fr[r["id"]] = r["verdict"].upper()

def mcnemar_pair(vA, vB, subset, correct_of):
    """b = A correct & B wrong ; c = B correct & A wrong"""
    b = c = 0
    for pid in subset:
        okA = (vA[pid] == correct_of[pid]); okB = (vB[pid] == correct_of[pid])
        if okA and not okB: b += 1
        elif okB and not okA: c += 1
    return b, c, mcnemar_exact(b, c)

correct_of = {pid: ("REJECT" if truth[pid]["truth"]=="BROKEN" else "APPROVE") for pid in truth}
broken = [p for p in truth if truth[p]["truth"]=="BROKEN"]
valid  = [p for p in truth if truth[p]["truth"]=="OK"]
pairs = [("EXEC vs DEEPSEEK", exec_v, ds), ("FRONTIER vs DEEPSEEK", fr, ds), ("EXEC vs FRONTIER", exec_v, fr)]
for name, A, B in pairs:
    for lbl, sub in [("broken(41)", broken), ("valid(29)", valid), ("all(70)", list(truth))]:
        b, c, p = mcnemar_pair(A, B, sub, correct_of)
        out[f"mcnemar {name} {lbl}"] = f"b={b} c={c} p={p:.4g}"
        print(f"  {name:22} {lbl:11} discordant b={b:>2} c={c:>2}  exact p = {p:.4g}")

print()
print("="*88)
print("SECTION C — Fisher exact: grader safety/fairness contrasts (unpaired framing)")
print("="*88)
tests = {
 "FPR: PROP(9/84) vs TEXT-SIM(82/84)": (9, 75, 82, 2),
 "FPR: PROP(9/84) vs STRUCT-SIM(81/84)": (9, 75, 81, 3),
 "FNR: PROP(0/137) vs TEXT-SIM(17/137)": (0, 137, 17, 120),
 "3arm pass-valid: EXEC(28/29) vs DS(11/29)": (28, 1, 11, 18),
 "3arm catch-broken: EXEC(41/41) vs DS(36/41)": (41, 0, 36, 5),
}
for name, (a, b, c, d) in tests.items():
    p = fisher_exact(a, b, c, d)
    out[f"fisher {name}"] = f"p={p:.4g}"
    print(f"  {name:46} p = {p:.4g}")

print()
print("="*88)
print("SECTION D — Frontier two-pass agreement (78-item standard corpus)")
print("="*88)
print("  flips 0/78 -> raw agreement 1.00, Cohen's kappa = 1.00")
out["frontier 2-pass agreement"] = "0/78 flips, kappa=1.00"

json.dump(out, open("paper_stats.json","w"), ensure_ascii=False, indent=1)
print("\nsaved paper_stats.json")
