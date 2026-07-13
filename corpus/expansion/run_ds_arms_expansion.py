# -*- coding: utf-8 -*-
"""DeepSeek arms on the expansion gate corpus: (1) affordable static review per
item; (2) simulated-student per objective (artifact-blind by construction).
Local machine + public API only."""
import json, os, sys, time, urllib.request, re
sys.path.insert(0,"."); import corpus_run as C
KEY=os.environ["DEEPSEEK_API_KEY"]; API="https://api.deepseek.com/chat/completions"
items=json.load(open("gate_items.json"))
cache={o["name"]:o for o in json.load(open("corpus_cache.json"))}
from specs import SPECS

def call(messages,temp,maxtok=1200):
    body=json.dumps({"model":"deepseek-chat","temperature":temp,"max_tokens":maxtok,"messages":messages}).encode()
    req=urllib.request.Request(API,data=body,headers={"Content-Type":"application/json","Authorization":"Bearer "+KEY})
    for a in range(5):
        try:
            with urllib.request.urlopen(req,timeout=180) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"]
        except Exception as e:
            if a==4: raise
            time.sleep(2*(a+1))
    return ""

REVIEW=("You are the quality-review layer of an AI tutoring system for a Verilog course. A tutor "
 "(another AI) proposed a fix for a student's buggy code. Decide by careful STATIC review only "
 "(no simulator) whether the proposed fix is safe to deliver to the student. Verdict: \"APPROVE\" "
 "(fix correctly implements the spec) or \"REJECT\" (fix is functionally wrong). Answer with exactly "
 "one word: APPROVE or REJECT.")

def review(spec,fix):
    u=f"Assignment spec:\n{spec}\n\nProposed corrected Verilog:\n{fix}\n\nVerdict (APPROVE or REJECT):"
    out=call([{"role":"system","content":REVIEW},{"role":"user","content":u}],0.0,20)
    return "APPROVE" if "APPROVE" in out.upper() else "REJECT"

def module_of(t):
    m=re.search(r"\bmodule\b.*?\bendmodule\b",t,re.S); return m.group(0) if m else None

# ---- (1) affordable review, per item ----
rev={}
OUT="arms_ds.json"
if os.path.exists(OUT): rev=json.load(open(OUT)).get("review",{})
t0=time.time()
for n,it in enumerate(items):
    if it["id"] in rev: continue
    rev[it["id"]]=review(it["spec"],it["rtl"])
    if (n+1)%20==0:
        json.dump({"review":rev},open(OUT,"w"))
        print(f"  review {n+1}/{len(items)}  ({time.time()-t0:.0f}s)",flush=True)
json.dump({"review":rev},open(OUT,"w"))
print(f"affordable review done: {len(rev)} items")

# ---- (2) simulated student, per objective (verdict reused for all its items) ----
TUTOR=("You are a Verilog tutor. Explain in <=25 words what is wrong with the student's module "
 "and how to fix it. Do not output code, only the explanation.")
STUD=("You are a student in a Verilog course. Using ONLY the tutor's explanation, rewrite the module "
 "to fix the bug. Output one COMPLETE compilable module, same name and ports.")
simobj={}
for oi,(name,o) in enumerate(cache.items()):
    buggy=o["buggys"][0][1]  # canonical provided bug
    expl=call([{"role":"system","content":TUTOR},
               {"role":"user","content":f"Spec: {SPECS.get(name,name)}\n\nStudent's buggy code:\n{buggy}\n\nExplanation:"}],0.0,120)
    passes=0
    for k in range(3):
        rep=call([{"role":"system","content":STUD},
                  {"role":"user","content":f"Spec: {SPECS.get(name,name)}\n\nYour buggy code:\n{buggy}\n\nTutor's explanation:\n{expl}\n\nCorrected module:"}],0.8,1600)
        mod=module_of(rep)
        if mod:
            pv,_=C.prop_grade(mod,o["ptb"],f"ss_{name}_{k}")
            if pv=="ACCEPT": passes+=1
    simobj[name]="APPROVE" if passes>=2 else "REJECT"
    print(f"  sim-student [{oi+1}/{len(cache)}] {name}: {passes}/3 -> {simobj[name]}",flush=True)
    json.dump({"review":rev,"sim_obj":simobj},open(OUT,"w"))
# expand per-objective sim verdict to per-item
sim={it["id"]:simobj[it["obj"]] for it in items}
json.dump({"review":rev,"sim_obj":simobj,"sim":sim},open(OUT,"w"))
print("sim-student done. saved arms_ds.json")
