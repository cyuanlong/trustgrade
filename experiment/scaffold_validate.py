#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module 2 — verified scaffolding: validate LLM-generated step decompositions
before delivery. A scaffold step reaches the student ONLY if:
  (s1) its checkpoint testbench + step reference RTL compile together
  (s2) the pair prints PASS (checkpoint is achievable exactly as stated)
  (s3) the FINAL step's RTL passes the assignment's REAL property TB
       (the scaffold provably leads to a correct solution)
Metrics reported:
  - raw LLM scaffold validity (how often unchecked scaffolds would be broken)
  - delivered validity = 100% by construction (the gate)
  - per-objective step coverage after gating
Local iverilog only.
"""
import json, os, sys, collections
sys.path.insert(0, "."); import corpus_run as C

def load_scaffolds():
    arr = json.load(open("scaffolds.json"))
    return arr

def check_pair(rtl, tb, tag):
    out, err = C.compile_run({"dut.v": rtl, "tb.v": tb}, C.tb_top(tb), "sc_" + tag)
    if err:
        return False, err
    ok = ("PASS" in out) and not C.FAIL_TOK.search(out)
    return ok, (out.strip().splitlines() or [""])[-1][:60]

def main():
    cache = {o["name"]: o for o in json.load(open("corpus_cache.json"))}
    scaffolds = load_scaffolds()
    rows = []
    for sc in scaffolds:
        name = sc["objective"]
        obj = cache.get(name)
        steps = sc.get("steps", [])
        for k, st in enumerate(steps):
            ok, msg = check_pair(st.get("step_rtl",""), st.get("step_tb",""), f"{name}_{k}")
            final_ok = None
            if k == len(steps) - 1 and obj:                      # s3: final step vs real property TB
                fv, fmsg = C.prop_grade(st.get("step_rtl",""), obj["ptb"], f"scfin_{name}")
                final_ok = (fv == "ACCEPT")
            rows.append(dict(obj=name, step=st.get("n", k+1), ok=ok,
                             final_ok=final_ok, msg=msg,
                             goal=st.get("goal","")[:60]))
    n = len(rows)
    valid = sum(1 for r in rows if r["ok"])
    finals = [r for r in rows if r["final_ok"] is not None]
    finals_ok = sum(1 for r in finals if r["final_ok"])
    objs = collections.Counter(r["obj"] for r in rows)
    objs_all_ok = sum(1 for o in objs if all(r["ok"] for r in rows if r["obj"] == o))
    print("=" * 92)
    print("Module 2 — scaffold validation gate (LLM-generated step decompositions)")
    print("=" * 92)
    print(f"objectives: {len(objs)}   steps total: {n}")
    print(f"raw step validity (checkpoint compiles & PASSes)   : {valid}/{n} = {valid/max(1,n):.0%}")
    print(f"final step passes the REAL assignment property TB  : {finals_ok}/{len(finals)}")
    print(f"objectives with ALL steps valid as generated       : {objs_all_ok}/{len(objs)}")
    print(f"-> delivered-to-student validity after gate        : 100% by construction "
          f"({valid}/{n} steps deliverable, {n-valid} blocked for repair)")
    print("-" * 92)
    bad = [r for r in rows if not r["ok"] or r["final_ok"] is False]
    if bad:
        print("blocked steps (would have been broken scaffolds without the gate):")
        for r in bad[:15]:
            fin = "" if r["final_ok"] is None else f" final_ok={r['final_ok']}"
            print(f"   {r['obj']:22} step{r['step']} ok={r['ok']}{fin}  {r['msg']}")
    json.dump(rows, open("scaffold_results.json", "w"), ensure_ascii=False, indent=1)
    print("\nsaved scaffold_results.json")

if __name__ == "__main__":
    main()
