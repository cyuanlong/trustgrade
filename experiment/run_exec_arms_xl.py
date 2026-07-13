# -*- coding: utf-8 -*-
"""Run the two execution arms on the expanded corpus (primary = valid + broken)."""
import json, sys, time
sys.path.insert(0,"."); import corpus_run as C
import trustgrade as TG
cache = {o["name"]: o for o in json.load(open("corpus_cache.json"))}
truth = {m["id"]: m for m in json.load(open("gatexl_truth.json"))}
items = json.load(open("gatexl_items.json"))
primary = [it for it in items if not truth[it["id"]]["src"].startswith("mutpres_")]
print("primary items:", len(primary))
res = {}
t0=time.time()
for n,it in enumerate(primary):
    o = cache[it["obj"]]
    a = TG.assess(it["rtl"], o)                      # full gate: deliver iff sound ACC
    full = "APPROVE" if (a["verdict"]=="ACC" if False else a["verdict"]=="ACC") else None
    full = "APPROVE" if (a["verdict"]=="ACC") else ("APPROVE" if a["verdict"]=="ACCEPT" and a["backing"].startswith("sound") else "REJECT")
    pv,_ = C.prop_grade(it["rtl"], o["ptb"], "xt_"+it["id"])   # test-only gate
    res[it["id"]] = dict(full=full, test="APPROVE" if pv=="ACCEPT" else "REJECT",
                         layer=a["layer"], verdict=a["verdict"])
    if (n+1)%50==0: print(f"  {n+1}/{len(primary)} ({time.time()-t0:.0f}s)", flush=True)
json.dump(res, open("gatexl_exec_verdicts.json","w"))

def score(arm):
    B=[p for p in res if truth[p]["truth"]=="BROKEN"]; K=[p for p in res if truth[p]["truth"]=="OK"]
    catch=sum(1 for p in B if res[p][arm]=="REJECT"); harm=len(B)-catch
    passed=sum(1 for p in K if res[p][arm]=="APPROVE")
    return catch,len(B),passed,len(K),harm
for arm,label in [("full","FULL execution gate"),("test","TEST-ONLY gate")]:
    c,nb,pv,nk,h = score(arm)
    print(f"{label:24} catch {c}/{nb}  pass-valid {pv}/{nk}  harmful {h}")
# where do the 9 property-evaders land under the full gate?
ev=[p for p in res if truth[p].get("evades_property")]
print("\nproperty-evading broken (n=%d): full-gate verdicts:"%len(ev))
import collections
print(" ", dict(collections.Counter(res[p]["verdict"] for p in ev)),
      "| delivered harmful by FULL:", sum(1 for p in ev if res[p]["full"]=="APPROVE"),
      "| by TEST-ONLY:", sum(1 for p in ev if res[p]["test"]=="APPROVE"))
