# -*- coding: utf-8 -*-
"""Grader comparison on the expansion corpus, with Wilson 95% CIs and Fisher
exact tests vs the property grader. Reads corpus_results.json (from corpus_run.py)
and trustgrade_results.json (backbone). Deterministic; no API."""
import json, math

def wilson(k,n,z=1.959964):
    if n==0: return (0.0,0.0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return (max(0,c-h),min(1,c+h))
def fisher(a,b,c,d):
    n=a+b+c+d; r1=a+b; c1=a+c
    def hg(x): return math.comb(c1,x)*math.comb(n-c1,r1-x)/math.comb(n,r1)
    po=hg(a); lo=max(0,r1+c1-n); hi=min(r1,c1)
    return min(1.0,sum(hg(x) for x in range(lo,hi+1) if hg(x)<=po+1e-12))

rows=json.load(open("corpus_results.json"))
V=[r for r in rows if r["truth"]=="VALID"]; B=[r for r in rows if r["truth"]=="BUGGY"]
A=[r for r in V if not r["is_golden"]]
nobj=len({r["obj"] for r in rows})
print("="*92)
print(f"EXPANSION CORPUS — grader comparison  ({nobj} objectives, {len(rows)} submissions:")
print(f"  VALID={len(V)} [alternatives={len(A)}], BUGGY={len(B)})")
print("="*92)
graders=[("prop","Property (ours)"),("refout","Reference-output match"),
         ("text_v","Token similarity"),("struct_v","Structural similarity")]
def rej(rowset,key): return sum(1 for r in rowset if r[key]=="REJECT")
def acc(rowset,key): return sum(1 for r in rowset if r[key]=="ACCEPT")
prop_fp=acc(B,"prop"); prop_ok=len(B)-prop_fp
print(f"{'grader':24} {'FNR valid':18} {'FNR alt':18} {'FPR buggy':18} {'Fisher vs PROP (FPR)':20}")
print("-"*92)
for key,label in graders:
    fnv=rej(V,key); lo1,hi1=wilson(fnv,len(V))
    fna=rej(A,key); lo2,hi2=wilson(fna,len(A))
    fp=acc(B,key); lo3,hi3=wilson(fp,len(B)); ok=len(B)-fp
    pval="" if key=="prop" else f"p={fisher(fp,ok,prop_fp,prop_ok):.2e}"
    print(f"{label:24} {fnv:>2}/{len(V):<3}[{lo1:.2f},{hi1:.2f}]  {fna:>2}/{len(A):<3}[{lo2:.2f},{hi2:.2f}]  "
          f"{fp:>2}/{len(B):<3}[{lo3:.2f},{hi3:.2f}]  {pval}")
print("-"*92)

# backbone (full gate) safety/fairness on the same corpus
tg=json.load(open("trustgrade_results.json"))
tv=[r for r in tg if r["truth"]=="CORRECT"]; tb=[r for r in tg if r["truth"]=="BUGGY"]
caught=sum(1 for r in tb if r["verdict"]=="REJECT")
passed=sum(1 for r in tv if r["verdict"] in ("ACCEPT",))
unc=sum(1 for r in tg if r["verdict"]=="UNCERTAIN")
sound=[r for r in tg if r["verdict"] in ("ACCEPT","REJECT") and r["backing"].startswith("sound")]
scor=sum(1 for r in sound if (r["truth"]=="CORRECT")==(r["verdict"]=="ACCEPT"))
lo,hi=wilson(scor,len(sound))
print("BACKBONE (full execution gate) on the expansion corpus:")
print(f"  sound-verdict accuracy : {scor}/{len(sound)} [{lo:.3f},{hi:.3f}]")
print(f"  buggy caught (sound)   : {caught}/{len(tb)}")
print(f"  valid delivered ACCEPT : {passed}/{len(tv)}   (rest -> UNCERTAIN escalation, not rejection)")
print(f"  escalated to human     : {unc}/{len(tg)}")
