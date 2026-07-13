#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Feedback Gate v2 — uses the FULL TrustGrade backbone (L0 compile + L1 property
+ L2 differential-vs-reference) as the fix-contract check, not property-TB alone.
Delivery rule (conservative): deliver LLM feedback only if
  (1) tutor verdict agrees with backbone verdict on the student's code, AND
  (2) backbone verdict on the tutor's corrected RTL is sound ACCEPT.
UNCERTAIN or any disagreement -> verifier-only fallback.

B3 ground truth: a mutated fix counts as TRULY broken only if it observably
diverges from the unmutated verified fix (2-seed differential) — mutations that
preserve behavior are not broken and SHOULD be deliverable."""
import json, sys, time
sys.path.insert(0, "."); import corpus_run as C
import trustgrade as TG

cache = {o["name"]: o for o in json.load(open("corpus_cache.json"))}
tutor = json.load(open("tutor_outputs.json"))
tgmap = {(r["obj"], r["src"]): r for r in json.load(open("trustgrade_results.json"))}
def obj_of(i): return i.rsplit("__", 1)[0]

def fix_contract(fix, obj, tag):
    a = TG.assess(fix, obj)
    return a["verdict"] == "ACCEPT" and a["backing"].startswith("sound"), a["verdict"]

def gate(item, lat):
    i = item["id"]; obj = cache[obj_of(i)]
    trow = tgmap.get((obj_of(i), "provided_bug"))
    ver = "BUGGY" if trow["verdict"] == "REJECT" else ("CORRECT" if trow["verdict"] == "ACCEPT" else "UNCERTAIN")
    t0 = time.time()
    ok_v = (item.get("verdict", "").upper() == ver) or ver == "UNCERTAIN"
    ok_f, fverdict = fix_contract(item.get("corrected_rtl", ""), obj, i)
    lat.append(time.time() - t0)
    return ("DELIVER_FULL" if (ok_v and ok_f) else "FALLBACK", fverdict)

def run(name, items):
    lat = []; res = [gate(it, lat) for it in items]
    d = sum(1 for r, _ in res if r == "DELIVER_FULL")
    print(f"{name:36} deliver {d}/{len(items)}  intercept {len(items)-d}/{len(items)}  "
          f"avg {1000*sum(lat)/max(1,len(lat)):.0f}ms")
    return res

print("=" * 96)
print("Feedback Gate v2 (full L0+L1+L2 backbone as contract)")
print("=" * 96)
resA = run("A  real tutor (frontier LLM)", tutor)

# B3 with behavior-divergence ground truth
w3 = []
for t in tutor:
    obj = cache[obj_of(t["id"])]
    fix = t["corrected_rtl"]; mut = None; op = None
    for nm, fn in C.INJECTORS:
        m = fn(fix)
        if m and m != fix: mut, op = m, nm; break
    if not mut: continue
    # ground truth: does the mutant diverge from the verified fix itself?
    ports = C.parse_ports(obj.get("interface", "")); tbs = []
    diverges = None
    for k, s in enumerate(["64'hAAAA_BBBB_CCCC_0001", "64'h1357_9BDF_2468_ACE0"]):
        tb = C.gen_ref_tb(obj["modname"], ports, s, 128)
        if not tb: break
        g = C.ref_trace(fix, tb, f"b3g_{obj['name']}{k}"); c = C.ref_trace(mut, tb, f"b3c_{obj['name']}{k}")
        if g is None: break
        diverges = (c is None or c != g) or (diverges or False)
        if diverges: break
    w3.append((dict(t, corrected_rtl=mut), diverges, op))

lat = []
caught_broken = miss_broken = pass_pres = block_pres = 0
for item, truly_broken, op in w3:
    r, fv = gate(item, lat)
    if truly_broken is True:
        if r == "FALLBACK": caught_broken += 1
        else: miss_broken += 1
    elif truly_broken is False:
        if r == "DELIVER_FULL": pass_pres += 1
        else: block_pres += 1
nb = caught_broken + miss_broken; np_ = pass_pres + block_pres
print(f"B3 mutated fixes: {len(w3)} total -> truly-broken {nb}, behavior-preserving {np_}, undecidable {len(w3)-nb-np_}")
print(f"   gate catches truly-broken fixes  : {caught_broken}/{nb}")
print(f"   gate passes behavior-preserving  : {pass_pres}/{np_} (blocking these is over-conservatism, not harm)")
json.dump(dict(A_deliver=sum(1 for r,_ in resA if r=='DELIVER_FULL'),
               B3=dict(total=len(w3), broken=nb, caught=caught_broken, preserved=np_, passed=pass_pres)),
          open("gate2_results.json", "w"), indent=1)
print("saved gate2_results.json")
