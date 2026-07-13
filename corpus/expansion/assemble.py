# -*- coding: utf-8 -*-
import json, glob, os
tasks=[]
for f in sorted(glob.glob("batches/batch_*.json")):
    b=json.load(open(f))
    for o in b: o.setdefault("interface", o.get("interface",""))
    tasks+=b
    print(f"  + {os.path.basename(f)}: {len(b)}")
json.dump(tasks, open("hard_tasks.json","w"), ensure_ascii=False)
print(f"hard_tasks.json: {len(tasks)} objectives")
