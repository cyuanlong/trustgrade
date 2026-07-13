# -*- coding: utf-8 -*-
"""DeepSeek arms on the expanded 222-item corpus: (1) static review; (2) simulated-student.
Local machine + public API only."""
import json, os, sys, time, urllib.request, re
sys.path.insert(0,"."); import corpus_run as C
KEY=os.environ["DEEPSEEK_API_KEY"]; API="https://api.deepseek.com/chat/completions"
truth={m["id"]:m for m in json.load(open("gatexl_truth.json"))}
cache={o["name"]:o for o in json.load(open("corpus_cache.json"))}
buggy_of=json.load(open("gatexl_buggy_of.json"))
items=[]
for i in range(8): items+=json.load(open(f"gatexl_batches/gb_{i}.json"))
items.sort(key=lambda x:x["id"])

def call(messages, temp, seed=None, maxtok=3000, fmt=None):
    body=dict(model="deepseek-chat",temperature=temp,max_tokens=maxtok,messages=messages)
    if seed is not None: body["seed"]=seed
    if fmt: body["response_format"]=fmt
    req=urllib.request.Request(API,data=json.dumps(body).encode(),
        headers={"Content-Type":"application/json","Authorization":"Bearer "+KEY})
    for a in range(4):
        try:
            with urllib.request.urlopen(req,timeout=180) as r:
                return json.load(r)["choices"][0]["message"]["content"]
        except Exception:
            time.sleep(4*(a+1))
    return ""

SYS=("You are the quality-review layer of an AI tutoring system for a Verilog course. "
     "Decide by careful STATIC review only (no simulator) whether the proposed fix is safe to deliver.")
rev=[]; t0=time.time()
for n,it in enumerate(items):
    user=(f"Assignment spec and interface:\n{it['spec']}\n\nTutor's explanation:\n{it['tutor_explanation']}\n\n"
          f"Proposed corrected code:\n```verilog\n{it['proposed_fix_rtl']}\n```\n\n"
          'Verdict: "APPROVE" or "REJECT". Judge on its own merits. Reply ONLY JSON: {"verdict":"...","reason":"<=12 words"}')
    txt=call([{"role":"system","content":SYS},{"role":"user","content":user}],0.0,fmt={"type":"json_object"})
    try: v=json.loads(txt).get("verdict","").upper()
    except Exception: v="ERROR"
    rev.append(dict(id=it["id"],verdict=v))
    if (n+1)%40==0: print(f"review {n+1}/222 ({time.time()-t0:.0f}s)",flush=True)
json.dump(rev,open("gatexl_ds_review.json","w"))
print("review arm done",flush=True)

sim=[]
for n,it in enumerate(items):
    o=cache[truth[it["id"]]["obj"]]; passes=0
    for k in range(3):
        user=(f"You are a student in a Verilog course. Your submission has a bug. Your tutor said:\n"
              f"\"{it['tutor_explanation']}\"\n\nAssignment:\n{it['spec']}\n\nYour current (buggy) code:\n"
              f"```verilog\n{buggy_of[it['id']]}\n```\n\nUsing the tutor's feedback, produce corrected code. "
              f"Reply ONLY the complete corrected Verilog module.")
        txt=call([{"role":"user","content":user}],0.8,seed=200+k)
        m=re.search(r"```(?:verilog)?\s*(.*?)```",txt,re.S)
        fx=(m.group(1) if m else txt).strip()
        if fx:
            v,_=C.prop_grade(fx,o["ptb"],f"sx_{it['id']}_{k}")
            if v=="ACCEPT": passes+=1
    sim.append(dict(id=it["id"],passes=passes,verdict="APPROVE" if passes>=2 else "REJECT"))
    if (n+1)%25==0: print(f"simstudent {n+1}/222 ({time.time()-t0:.0f}s)",flush=True)
json.dump(sim,open("gatexl_ds_simstudent.json","w"))
print("sim-student arm done",flush=True)
