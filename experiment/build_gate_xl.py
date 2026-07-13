# -*- coding: utf-8 -*-
"""Expanded gate corpus (target ~250 items): all 37 objectives, ALL applicable
mutation operators on each golden (oracle-confirmed), lazy fixes from every
provided bug, and the full valid class as 'fix' artifacts. Flags property-evading
broken items (the class that can separate the top gates). Local only."""
import json, sys, random
sys.path.insert(0,"."); import corpus_run as C
import trustgrade as TG

cache = json.load(open("corpus_cache.json"))
tutor_expl = {}
for t in json.load(open("tutor_outputs.json")):
    tutor_expl[t["id"].rsplit("__",1)[0]] = t["explanation"]
NEUTRAL = "The previous attempt contained a functional bug; the following is the corrected implementation."

items = []
stats = {"valid":0,"lazy":0,"mut_broken":0,"mut_preserving":0,"evading":0}
for o in cache:
    name = o["name"]; golden = o["golden"]
    ports = C.parse_ports(o.get("interface","")); 
    spec = f"SPEC-ID {name}"  # spec text pulled at batch build time
    expl = tutor_expl.get(name, NEUTRAL)
    # oracle traces for golden (2 seeds x 128)
    tbs, gts = [], []
    okG = True
    for k,s in enumerate(["64'hAAAA_BBBB_CCCC_0001","64'h1357_9BDF_2468_ACE0"]):
        tb = C.gen_ref_tb(o["modname"], ports, s, 128)
        if not tb: okG=False; break
        g = C.ref_trace(golden, tb, f"xg_{name}{k}")
        if g is None: okG=False; break
        tbs.append(tb); gts.append(g)
    # VALID fixes: golden + variants + alternates (all already construction-verified)
    for src, rtl in o["valids"]:
        items.append(dict(obj=name, src="valid_"+src, truth="OK", rtl=rtl, expl=expl))
        stats["valid"] += 1
    # LAZY fix: provided bug returned as the fix
    for src, rtl in o["buggys"]:
        if src == "provided_bug":
            items.append(dict(obj=name, src="lazy", truth="BROKEN", rtl=rtl, expl=expl))
            stats["lazy"] += 1
    # MUTANTS: all applicable operators on golden, oracle-labeled
    if okG:
        for opname, fn in C.INJECTORS:
            mut = fn(golden)
            if not mut or mut == golden: continue
            div = None
            for k, tb in enumerate(tbs):
                ct = C.ref_trace(mut, tb, f"xm_{name}_{opname}{k}")
                div = (ct is None or ct != gts[k])
                if div: break
            if div is None: continue
            if div:
                pv,_ = C.prop_grade(mut, o["ptb"], f"xp_{name}_{opname}")
                evade = (pv == "ACCEPT")
                items.append(dict(obj=name, src=f"mut_{opname}", truth="BROKEN", rtl=mut,
                                  expl=expl, evades_property=evade))
                stats["mut_broken"] += 1; stats["evading"] += int(evade)
            else:
                items.append(dict(obj=name, src=f"mutpres_{opname}", truth="OK", rtl=mut, expl=expl))
                stats["mut_preserving"] += 1

random.seed(23); random.shuffle(items)
mapping=[]; pub=[]
for i,it in enumerate(items):
    pid=f"gx_{i:03d}"
    mapping.append(dict(id=pid, **{k:v for k,v in it.items() if k!="rtl" and k!="expl"}))
    pub.append(dict(id=pid, obj=it["obj"], rtl=it["rtl"], expl=it["expl"]))
json.dump(mapping, open("gatexl_truth.json","w"), ensure_ascii=False, indent=1)
json.dump(pub, open("gatexl_items.json","w"), ensure_ascii=False)
nb=sum(1 for m in mapping if m["truth"]=="BROKEN"); nk=len(mapping)-nb
print(f"EXPANDED GATE CORPUS: {len(mapping)} items = {nb} BROKEN + {nk} OK")
print("breakdown:", stats)
