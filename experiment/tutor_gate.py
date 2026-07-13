#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Feedback Gate — the cross-check layer of Module 1 (trustworthy assessment).

Design: NOTHING the LLM tutor says reaches the learner unchecked.
  check-1 verdict-consistency : tutor verdict must agree with the verifier backbone
  check-2 fix-contract        : tutor's corrected RTL must compile + pass the property TB
If both hold -> deliver full feedback (verdict + explanation + verified fix).
Else -> deliver verifier-only fallback (sound verdict + diagnosis, no unverified prose).

Evaluation:
  A) real tutor (frontier LLM, 35 items)  -> delivery rate, gate latency
  B) simulated faulty tutors (weak/cheap models):
     W1 verdict-flip  (says CORRECT on buggy code)
     W2 lazy-fix      (returns the student's buggy code as the "fix")
     W3 broken-fix    (fix mutated by an injector)
     -> how much faulty feedback WOULD reach students without the gate vs with it.
Local iverilog only.
"""
import json, os, sys, time
sys.path.insert(0, "."); import corpus_run as C

cache  = {o["name"]: o for o in json.load(open("corpus_cache.json"))}
tutor  = json.load(open("tutor_outputs.json"))
vref   = json.load(open("tutor_verify_ref.json"))
tgmap  = {(r["obj"], r["src"]): r for r in json.load(open("trustgrade_results.json"))}

def obj_of(i): return i.rsplit("__", 1)[0]

def gate(item, lat):
    i = item["id"]; obj = obj_of(i); r = vref[i]
    trow = tgmap.get((obj, "provided_bug"))
    t0 = time.time()
    ver = "BUGGY" if trow["verdict"] == "REJECT" else ("CORRECT" if trow["verdict"] == "ACCEPT" else "UNCERTAIN")
    ok_verdict = (item.get("verdict", "").upper() == ver) or ver == "UNCERTAIN"
    fix = item.get("corrected_rtl", "")
    fv, _ = C.prop_grade(fix, r["ptb"], "gate_" + i.replace("/", "_")[:44]) if fix.strip() else ("REJECT", "")
    lat.append(time.time() - t0)
    ok_fix = (fv == "ACCEPT")
    if ok_verdict and ok_fix:
        return "DELIVER_FULL", None
    why = []
    if not ok_verdict: why.append("verdict-contradicts-verifier")
    if not ok_fix:     why.append("fix-fails-contract")
    return "FALLBACK_VERIFIER_ONLY", "+".join(why)

def run(name, items):
    lat = []; delivered = 0; intercepted = []
    for it in items:
        d, why = gate(it, lat)
        if d == "DELIVER_FULL": delivered += 1
        else: intercepted.append((it["id"], why))
    n = len(items)
    print(f"{name:34} delivered-full {delivered}/{n}   intercepted {n-delivered}/{n}"
          f"   avg-gate-latency {1000*sum(lat)/max(1,len(lat)):.0f}ms")
    return intercepted

print("=" * 96)
print("Feedback Gate evaluation — cross-checked LLM tutoring layer (Module 1)")
print("=" * 96)

# A) real frontier tutor
inter_A = run("A  real tutor (frontier LLM)", tutor)

# B) simulated faulty tutors
w1 = [dict(t, verdict="CORRECT") for t in tutor]                        # missed-bug verdicts
w2 = []                                                                  # lazy: returns buggy code as fix
for t in tutor:
    buggy = [rtl for s, rtl in cache[obj_of(t["id"])]["buggys"] if s == "provided_bug"][0]
    w2.append(dict(t, corrected_rtl=buggy))
w3 = []                                                                  # broken fix via injectors
for t in tutor:
    mut = None
    for _, fn in C.INJECTORS:
        mut = fn(t["corrected_rtl"])
        if mut and mut != t["corrected_rtl"]: break
    w3.append(dict(t, corrected_rtl=mut or t["corrected_rtl"]))

inter_1 = run("B1 faulty: verdict-flip", w1)
inter_2 = run("B2 faulty: lazy-fix (unfixed code)", w2)
inter_3 = run("B3 faulty: mutated/broken fix", w3)

print("-" * 96)
n = len(tutor)
harm = {"B1": n - 0, "B2": n, "B3": n}  # without gate, ALL faulty items reach students
print("without gate: 100% of faulty tutor feedback reaches students; with gate:")
for nm, inter in [("B1", inter_1), ("B2", inter_2), ("B3", inter_3)]:
    print(f"   {nm}: {len(inter)}/{n} intercepted -> {n-len(inter)} reach students")
note3 = [i for i, w in inter_3]
json.dump(dict(A=[i for i, _ in inter_A], B1=[i for i, _ in inter_1],
               B2=[i for i, _ in inter_2], B3=[i for i, _ in inter_3]),
          open("gate_results.json", "w"), indent=1)
print("\nsaved gate_results.json")
