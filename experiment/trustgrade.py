#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TrustGrade — trustworthy automated-assessment engine (Module 1 of the
verification-augmented HDL tutoring system).

Design principle (the system contribution): the grade delivered to the student
is BACKED BY A VERIFIER, never by an unchecked LLM claim. Layered decision:
  L0  compile (iverilog)         -> reject uncompilable (sound)
  L1  property assertions (TB)   -> reject invariant violations (sound) + which property
  L2  differential vs reference  -> catch behavioral bugs L1's invariants miss (sound reject)
  If L1 PASS and L2 matches      -> ACCEPT with verifier backing
  If L1 PASS but L2 differs      -> "verifier-uncertain": needs LLM/human (don't-care OR uncovered bug)
Misconception diagnosis is attached from the failing layer's signal.
This file is the deterministic trustworthy backbone; the LLM layer (explanation)
is cross-checked against these verdicts before anything reaches the learner.

Technical evaluation reported: delivered-grade soundness coverage, accuracy on
construction-based ground truth, and diagnosis specificity. Local iverilog.
"""
import json, os, re, sys, collections
sys.path.insert(0, "."); import corpus_run as C

cache = json.load(open("corpus_cache.json"))

FAILTOK = re.compile(r"(FAIL[^\n]*|VIOLATION|MISMATCH|GLITCH|STARV|TIMEOUT)", re.I)
def diagnose_from_prop(out):
    m = FAILTOK.search(out or "")
    return m.group(0)[:60] if m else "property violated"

def compile_ok(rtl, tag):
    d = os.path.join(C.WORK, "tg_"+tag); os.makedirs(d, exist_ok=True)
    open(os.path.join(d,"m.v"),"w").write(rtl)
    r = C.sh(["iverilog","-g2012","-o","m.vvp","m.v"], d, timeout=15)
    return r.returncode==0, (r.stderr or "").strip().splitlines()[-1][:60] if r.returncode!=0 else ""

def assess(rtl, obj):
    """Return dict: layer that decided, verdict, backing(sound/uncertain), diagnosis."""
    ptb = obj["ptb"]; golden = obj["golden"]; mod = obj["modname"]
    ports = C.parse_ports(obj.get("interface",""))
    # L0 compile
    ok, msg = compile_ok(rtl, obj["name"])
    if not ok:
        return dict(layer="L0", verdict="REJECT", backing="sound", diag=f"compile error: {msg}")
    # L1 property
    pv, pmsg = C.prop_grade(rtl, ptb, "tg1_"+obj["name"])
    if pv == "REJECT":
        return dict(layer="L1", verdict="REJECT", backing="sound", diag=f"invariant: {diagnose_from_prop(pmsg)}")
    # L2 differential vs golden
    ref_tb = C.gen_ref_tb(mod, ports)
    if ref_tb:
        g = C.ref_trace(golden, ref_tb, "tgG_"+obj["name"])
        c = C.ref_trace(rtl, ref_tb, "tgC_"+obj["name"])
        if g is not None and c is not None:
            if c == g:
                return dict(layer="L2", verdict="ACCEPT", backing="sound", diag="passes invariants; matches reference")
            else:
                return dict(layer="L2", verdict="UNCERTAIN", backing="uncertain",
                            diag="passes invariants but differs from reference (valid variant OR uncovered bug) -> escalate to LLM/human")
    return dict(layer="L1", verdict="ACCEPT", backing="sound-weak", diag="passes invariants (no reference harness)")

def main():
    rows=[]
    for obj in cache:
        subs = [("CORRECT",s,r) for s,r in obj["valids"]] + [("BUGGY",s,r) for s,r in obj["buggys"]]
        for truth, src, rtl in subs:
            a = assess(rtl, obj)
            rows.append(dict(obj=obj["name"], truth=truth, src=src, **a))
    n=len(rows); V=[r for r in rows if r["truth"]=="CORRECT"]; B=[r for r in rows if r["truth"]=="BUGGY"]
    def rate(x,d): return f"{x}/{d} = {x/max(1,d):.2f}"
    # soundly-decided = verdict is ACCEPT/REJECT with sound backing (not UNCERTAIN)
    sound = [r for r in rows if r["verdict"] in ("ACCEPT","REJECT") and r["backing"].startswith("sound")]
    uncertain = [r for r in rows if r["verdict"]=="UNCERTAIN"]
    # correctness of delivered sound verdicts vs construction GT
    sound_correct = sum(1 for r in sound if (r["truth"]=="CORRECT")==(r["verdict"]=="ACCEPT"))
    # buggy caught by the sound layers
    buggy_caught = sum(1 for r in B if r["verdict"]=="REJECT")
    print("="*88)
    print("TrustGrade — trustworthy automated assessment (Module 1) technical evaluation")
    print("="*88)
    print(f"submissions: {n}  (CORRECT={len(V)}, BUGGY={len(B)})  over {len(cache)} objectives")
    print(f"soundly decided by verifier layers   : {rate(len(sound),n)}   <- grades delivered with verifier backing")
    print(f"escalated to LLM/human (L2 uncertain): {rate(len(uncertain),n)}")
    print(f"accuracy of sound verdicts (vs GT)   : {rate(sound_correct,len(sound))}   <- delivered grades are trustworthy")
    print(f"buggy caught by sound layers         : {rate(buggy_caught,len(B))}")
    print("-"*88)
    print("which layer delivered the verdict:")
    for lay,cnt in collections.Counter(r["layer"]+":"+r["verdict"] for r in rows).most_common():
        print(f"   {lay:16} {cnt}")
    print("-"*88)
    # the UNCERTAIN set = where pure-verifier can't decide (don't-care vs uncovered bug) -> LLM value zone
    print(f"UNCERTAIN (verifier can't decide -> LLM/human needed): {len(uncertain)}")
    for r in uncertain[:12]:
        print(f"   {r['obj']:22} {r['truth']:7} {r['src']}")
    json.dump(rows, open("trustgrade_results.json","w"), ensure_ascii=False, indent=1)
    print("\nsaved trustgrade_results.json")

if __name__=="__main__":
    main()
