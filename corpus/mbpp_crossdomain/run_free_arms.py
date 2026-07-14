# -*- coding: utf-8 -*-
import json, re
from py_exec import run_tests
items=json.load(open("mbpp_items.json"))
golden={it["tid"]:it["code"] for it in items if it["id"].endswith("__golden")}
def toks(s):
    s=re.sub(r"#[^\n]*","",s)
    return set(re.findall(r"[A-Za-z_]\w*|\d+|\S",s))
def jacc(a,b):
    A,B=toks(a),toks(b); return len(A&B)/max(1,len(A|B))
res={}
for it in items:
    ev=run_tests(it["code"],it["setup"],it["tests"])
    sim=jacc(it["code"],golden[it["tid"]])
    res[it["id"]]=dict(exec_="APPROVE" if ev=="PASS" else "REJECT",
                       sim=sim, sim_v="APPROVE" if sim>=0.8 else "REJECT",
                       truth=it["truth"])
json.dump(res,open("arms_free.json","w"))
B=[i for i in res if res[i]["truth"]=="BROKEN"]; K=[i for i in res if res[i]["truth"]=="OK"]
for arm,key in [("Execution gate (ours)","exec_"),("Token similarity","sim_v")]:
    catch=sum(1 for i in B if res[i][key]=="REJECT"); passv=sum(1 for i in K if res[i][key]=="APPROVE")
    harm=sum(1 for i in B if res[i][key]=="APPROVE")
    print(f"{arm:24} catch {catch}/{len(B)}  pass {passv}/{len(K)}  harmful {harm}")
