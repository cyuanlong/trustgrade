#!/usr/bin/env python3
# Build the 13-objective construction submission set locally (no simulation needed).
import json, os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import corpus_run as C

subs = []
def add(obj, src, truth, spec, rtl):
    subs.append(dict(id=f"{obj}__{src}", obj=obj, src=src, truth=truth, spec=spec, rtl=rtl))

tasks = json.load(open(os.path.join(HERE, "hard_tasks.json")))
for t in tasks:
    g = t["golden_rtl"]; ptb = t["property_tb"]
    spec = f"SPEC: {t['spec']}\nPRINCIPLE: {t['principle']}\nINTERFACE: {t['interface']}"
    add(t["name"], "golden", "VALID", spec, g)
    rf = C.variant_reformat(g)
    if C.is_alpha_equiv(g, rf): add(t["name"], "variant_reformat", "VALID", spec, rf)
    for i in range(2):
        v = C.variant_rename(g, f"r{i}", tb=ptb)
        if v and C.is_alpha_equiv(g, v): add(t["name"], f"variant_rename{i}", "VALID", spec, v)
    add(t["name"], "provided_bug", "BUGGY", spec, t["buggy_rtl"])

arb = json.load(open(os.path.join(HERE, "arb_bundle.json")))
arb_spec = ("SPEC: 4-request round-robin arbiter. INTERFACE: module arbiter_rr(input clk, input rst_n, "
            "input [3:0] req, output [3:0] grant). PROPERTIES: P1 grant is one-hot0 (mutual exclusion); "
            "P2 never grant an idle line (grant & ~req)==0; P3 fairness: a continuously-asserted request "
            "must be granted within a bounded number of cycles (no starvation).")
for c in arb["correct"]: add("rr_arbiter", f"alt_{c['name']}", "VALID", arb_spec, c["rtl"])
for b in arb["broken"]:  add("rr_arbiter", b["name"], "BUGGY", arb_spec, b["rtl"])

json.dump(subs, open(os.path.join(HERE, "submissions.json"), "w"), ensure_ascii=False, indent=1)
import collections
byobj = collections.Counter(s["obj"] for s in subs)
nv = sum(1 for s in subs if s["truth"]=="VALID"); nb = sum(1 for s in subs if s["truth"]=="BUGGY")
print(f"built {len(subs)} submissions across {len(byobj)} objectives (VALID={nv}, BUGGY={nb})")
print("per objective:", dict(byobj))
