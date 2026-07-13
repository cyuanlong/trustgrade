# -*- coding: utf-8 -*-
import json, sys
sys.path.insert(0,"."); import corpus_run as C; import trustgrade as TG
from specs import SPECS
cache=json.load(open("corpus_cache.json"))
items=[]; 
for o in cache:
    for src,rtl in o["valids"]: items.append(dict(id=f"{o['name']}__{src}",obj=o["name"],truth="OK",rtl=rtl,spec=SPECS.get(o["name"],o["name"])))
    for src,rtl in o["buggys"]: items.append(dict(id=f"{o['name']}__{src}",obj=o["name"],truth="BROKEN",rtl=rtl,spec=SPECS.get(o["name"],o["name"])))
json.dump(items,open("gate_items.json","w"),ensure_ascii=False)
objmap={o["name"]:o for o in cache}
# deterministic arms
res={}
for it in items:
    o=objmap[it["obj"]]
    pv,_=C.prop_grade(it["rtl"],o["ptb"],"ga_"+it["id"].replace("/","_")[:50])
    a=TG.assess(it["rtl"],o)
    full="APPROVE" if (a["verdict"]=="ACCEPT" and a["backing"].startswith("sound")) else "REJECT"
    res[it["id"]]=dict(ungated="APPROVE",test="APPROVE" if pv=="ACCEPT" else "REJECT",full=full,
                       truth=it["truth"])
json.dump(res,open("arms_exec.json","w"))
n=len(items); nok=sum(1 for i in items if i["truth"]=="OK"); nb=n-nok
print(f"gate items: {n} (OK={nok}, BROKEN={nb})")
print("deterministic arms written -> arms_exec.json")
