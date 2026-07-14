# -*- coding: utf-8 -*-
"""Cross-domain (Python/MBPP) comparison: our execution gate vs other LLM judges
vs similarity. 478 candidates (300 correct, 178 buggy), construction-based labels."""
import json, glob, math
def wilson(k,n,z=1.959964):
    if n==0:return(0,0)
    p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return(max(0,c-h),min(1,c+h))
def mcnemar(b,c):
    n=b+c
    if n==0:return 1.0
    k=min(b,c);return min(1.0,2*sum(math.comb(n,i) for i in range(k+1))*0.5**n)
items=json.load(open("mbpp_items.json")); truth={it["id"]:it["truth"] for it in items}
free=json.load(open("arms_free.json"))
arms={"Execution gate (ours)":{i:free[i]["exec_"] for i in free},
      "Token similarity":{i:free[i]["sim_v"] for i in free}}
try: arms["DeepSeek judge"]=json.load(open("arms_ds_judge.json"))
except: pass
fj={}
for f in sorted(glob.glob("fjudge_*.json")):
    for r in json.load(open(f)): fj[r["id"]]=r["verdict"].upper()
if fj: arms["Claude judge (frontier)"]=fj
B=[i for i in truth if truth[i]=="BROKEN"]; K=[i for i in truth if truth[i]=="OK"]
def correct(v,i):
    x=v.get(i,"APPROVE"); return (x=="REJECT") if truth[i]=="BROKEN" else (x=="APPROVE")
ex=arms["Execution gate (ours)"]
print(f"MBPP corpus: {len(items)} candidates ({len(K)} correct, {len(B)} buggy)")
print(f"{'arm':26} {'catch buggy':18} {'pass correct':18} {'harmful':8} {'vs exec-gate'}")
print("-"*92)
for a,v in arms.items():
    cov=[i for i in truth if i in v]
    catch=sum(1 for i in B if v.get(i)=="REJECT"); lo,hi=wilson(catch,len(B))
    passv=sum(1 for i in K if v.get(i)=="APPROVE"); lo2,hi2=wilson(passv,len(K))
    harm=sum(1 for i in B if v.get(i)=="APPROVE")
    if a=="Execution gate (ours)": mc="—"
    else:
        b=sum(1 for i in truth if correct(ex,i) and not correct(v,i))
        c=sum(1 for i in truth if correct(v,i) and not correct(ex,i))
        mc=f"b={b},c={c},p={mcnemar(b,c):.2g}"
    note="" if len(cov)==len(truth) else f" (cov {len(cov)}/{len(truth)})"
    print(f"{a:26} {catch:>3}/{len(B)}[{lo:.2f},{hi:.2f}] {passv:>3}/{len(K)}[{lo2:.2f},{hi2:.2f}]  {harm:>3}    {mc}{note}")
