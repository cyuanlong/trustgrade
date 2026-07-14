# -*- coding: utf-8 -*-
"""DeepSeek judge (affordable 'other LLM'), reasoning allowed then a final verdict —
same affordance a real tutoring reviewer (and the frontier arm) gets. Static only."""
import json, os, time, urllib.request, re
KEY=os.environ["DEEPSEEK_API_KEY"]; API="https://api.deepseek.com/chat/completions"
items=json.load(open("mbpp_items.json"))
SYS=("You are the code-review layer of a programming tutor. Given a problem statement and a "
 "candidate Python solution, decide by careful STATIC review (do NOT execute) whether the solution "
 "correctly solves the problem for all valid inputs. Think briefly, then end your reply with a "
 "final line exactly of the form 'VERDICT: CORRECT' or 'VERDICT: BUGGY'.")
def judge(spec,code):
    body=json.dumps({"model":"deepseek-chat","temperature":0,"max_tokens":400,
      "messages":[{"role":"system","content":SYS},
      {"role":"user","content":f"Problem:\n{spec}\n\nCandidate solution:\n{code}\n\nReview, then give VERDICT:"}]}).encode()
    req=urllib.request.Request(API,data=body,headers={"Content-Type":"application/json","Authorization":"Bearer "+KEY})
    for a in range(5):
        try:
            with urllib.request.urlopen(req,timeout=120) as r:
                out=json.loads(r.read())["choices"][0]["message"]["content"]
                m=re.findall(r"VERDICT:\s*(CORRECT|BUGGY)",out.upper())
                if m: return "APPROVE" if m[-1]=="CORRECT" else "REJECT"
                return "APPROVE" if ("CORRECT" in out.upper() and "BUGGY" not in out.upper()) else "REJECT"
        except Exception:
            if a==4: return "ERROR"
            time.sleep(2*(a+1))
OUT="arms_ds_judge.json"
res={}  # fresh (prompt changed)
t0=time.time()
for n,it in enumerate(items):
    res[it["id"]]=judge(it["spec"],it["code"])
    if (n+1)%40==0: json.dump(res,open(OUT,"w")); print(f"  {n+1}/{len(items)} ({time.time()-t0:.0f}s)",flush=True)
json.dump(res,open(OUT,"w"))
print("DeepSeek judge (reasoning) done:",len(res))
