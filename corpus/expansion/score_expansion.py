# -*- coding: utf-8 -*-
"""Six-arm scoring on the expansion gate corpus (152 items: 88 OK, 64 BROKEN)."""
import json, glob, math
def wilson(k,n,z=1.959964):
    if n==0: return (0,0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return (max(0,c-h),min(1,c+h))
def mcnemar(b,c):
    n=b+c
    if n==0: return 1.0
    k=min(b,c); return min(1.0,2*sum(math.comb(n,i) for i in range(k+1))*0.5**n)

items=json.load(open("gate_items.json"))
truth={it["id"]:it["truth"] for it in items}
exc=json.load(open("arms_exec.json"))
ds=json.load(open("arms_ds.json"))
fr={}
for f in sorted(glob.glob("frontier/verdicts_*.json")):
    for r in json.load(open(f)): fr[r["id"]]=r["verdict"].upper()

arms={
 "Ungated":{i:"APPROVE" for i in truth},
 "Simulated student":ds["sim"],
 "Affordable review":ds["review"],
 "Frontier review":fr,
 "Test-only":{i:exc[i]["test"] for i in truth},
 "Full gate (ours)":{i:exc[i]["full"] for i in truth},
}
B=[i for i in truth if truth[i]=="BROKEN"]; K=[i for i in truth if truth[i]=="OK"]
# evaders = broken items the property testbench passes (test-only approves)
evaders=[i for i in B if exc[i]["test"]=="APPROVE"]
# correctness per item: harmful withheld (BROKEN->REJECT) or valid delivered (OK->APPROVE)
def correct(arm,i):
    v=arms[arm].get(i,"APPROVE")
    return (v=="REJECT") if truth[i]=="BROKEN" else (v=="APPROVE")
full="Full gate (ours)"
print(f"{'arm':22} {'catch broken':13} {'pass valid':12} {'evaders':9} {'harmful':8} {'McNemar vs full'}")
print("-"*92)
for a in arms:
    v=arms[a]
    catch=sum(1 for i in B if v.get(i)=="REJECT")
    passv=sum(1 for i in K if v.get(i)=="APPROVE")
    ev=sum(1 for i in evaders if v.get(i)=="REJECT")
    harm=sum(1 for i in B if v.get(i)=="APPROVE")
    if a==full: mc="—"
    else:
        b=sum(1 for i in truth if correct(full,i) and not correct(a,i))
        c=sum(1 for i in truth if correct(a,i) and not correct(full,i))
        mc=f"b={b},c={c},p={mcnemar(b,c):.2g}"
    lo,hi=wilson(catch,len(B)); lo2,hi2=wilson(passv,len(K))
    print(f"{a:22} {catch:>2}/{len(B)} [{lo:.2f},{hi:.2f}]  {passv:>3}/{len(K)}[{lo2:.2f},{hi2:.2f}] {ev:>2}/{len(evaders):<5} {harm:>3}      {mc}")
print("-"*92)
print(f"corpus: {len(items)} items ({len(K)} OK, {len(B)} BROKEN incl {len(evaders)} property-evaders)")
