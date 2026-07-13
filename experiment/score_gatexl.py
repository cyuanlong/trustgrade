# -*- coding: utf-8 -*-
"""Final six-arm scoring on the expanded 222-item corpus."""
import json, sys, re, html, math

def wilson(k,n,z=1.959964):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)
def mcn(b,c):
    n=b+c
    if n==0: return 1.0
    k=min(b,c)
    return min(1.0, 2*sum(math.comb(n,i) for i in range(k+1))*0.5**n)

truth={m["id"]:m for m in json.load(open("gatexl_truth.json"))}
primary=[p for p in truth if not truth[p]["src"].startswith("mutpres_")]
B=[p for p in primary if truth[p]["truth"]=="BROKEN"]; K=[p for p in primary if truth[p]["truth"]=="OK"]

execv=json.load(open("gatexl_exec_verdicts.json"))
arms={"full":{p:execv[p]["full"] for p in primary},
      "test":{p:execv[p]["test"] for p in primary},
      "ungated":{p:"APPROVE" for p in primary}}
arms["ds_review"]={r["id"]:r["verdict"] for r in json.load(open("gatexl_ds_review.json"))}
arms["simstudent"]={r["id"]:r["verdict"] for r in json.load(open("gatexl_ds_simstudent.json"))}

def last_array(fp):
    txt=None
    for line in open(fp):
        try:o=json.loads(line)
        except:continue
        m=o.get("message",{})
        if m.get("role")=="assistant":
            c=m.get("content");s=""
            if isinstance(c,str):s=c
            elif isinstance(c,list):
                for bb in c:
                    if isinstance(bb,dict) and bb.get("type")=="text":s+=bb.get("text","")
            if '"verdict"' in s:txt=s
    starts=[mm.start() for mm in re.finditer(r'\[\s*\{\s*"id"',txt)]
    raw=txt[starts[-1]:txt.rfind("]")+1]
    for cand in (raw,html.unescape(raw)):
        try:return json.loads(cand)
        except:pass
T="/private/tmp/claude-501/-Users-chenyuanlong/2e0da6f1-ae7f-4fbe-b6b5-dc0fa270c65f/tasks"
fr={}
for f in sys.argv[1:]:
    for r in last_array(f"{T}/{f}.output"):
        fr[r["id"]]=r["verdict"].upper()
# dedupe (batch1 had a duplicate id with correction — last wins already)
arms["frontier"]=fr

def correct(p,v):
    want="REJECT" if truth[p]["truth"]=="BROKEN" else "APPROVE"
    return v==want
rows=[]
order=[("ungated","Ungated"),("simstudent","Sim-student (GPT4Hints)"),("ds_review","Affordable review"),
       ("frontier","Frontier review"),("test","Test-only (CodeTailor)"),("full","Full execution gate")]
print(f"n = {len(primary)} (BROKEN {len(B)} incl. 9 property-evading / OK {len(K)})\n")
print(f"{'arm':26} {'catch broken':18} {'pass valid':18} {'harmful':8} {'McNemar vs full':>18}")
for key,label in order:
    V=arms[key]; miss=[p for p in primary if p not in V or V[p] not in("APPROVE","REJECT")]
    catch=sum(1 for p in B if V.get(p)=="REJECT"); harm=len(B)-catch
    passed=sum(1 for p in K if V.get(p)=="APPROVE")
    b=sum(1 for p in primary if correct(p,arms['full'].get(p)) and not correct(p,V.get(p,"")))
    c=sum(1 for p in primary if correct(p,V.get(p,"")) and not correct(p,arms['full'].get(p)))
    lo,hi=wilson(catch,len(B)); lo2,hi2=wilson(passed,len(K))
    mc="—" if key=="full" else f"b={b},c={c},p={mcn(b,c):.2g}"
    print(f"{label:26} {catch}/{len(B)} [{lo:.2f},{hi:.2f}]   {passed}/{len(K)} [{lo2:.2f},{hi2:.2f}]   {harm:<8} {mc:>18}" + (f"  (missing:{len(miss)})" if miss else ""))
# evading subset head-to-head
ev=[p for p in B if truth[p].get("evades_property")]
print(f"\nproperty-evading broken (n={len(ev)}) caught by:", {label:sum(1 for p in ev if arms[k].get(p)=='REJECT') for k,label in order})
json.dump({k:{p:v for p,v in V.items()} for k,V in arms.items()}, open("gatexl_all_verdicts.json","w"))
