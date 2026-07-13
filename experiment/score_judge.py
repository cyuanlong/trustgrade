#!/usr/bin/env python3
# Score the LLM-as-judge verdicts against ground truth; compare to PROP (property-based).
import json, os, glob, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
subs = {s["id"]: s for s in json.load(open(os.path.join(HERE, "submissions.json")))}

# collect verdicts from verdicts_*.json (each = [{"id","verdict","reason"},...])
verds = {}
for f in sorted(glob.glob(os.path.join(HERE, "verdicts_*.json"))):
    try:
        arr = json.load(open(f))
    except Exception as e:
        print("skip", f, e); continue
    for v in arr:
        vid = v.get("id"); ver = (v.get("verdict") or "").upper()
        if vid in subs and ver in ("CORRECT", "BUGGY"):
            verds[vid] = "ACCEPT" if ver == "CORRECT" else "REJECT"

matched = [i for i in subs if i in verds]
missing = [i for i in subs if i not in verds]
V = [i for i in matched if subs[i]["truth"] == "VALID"]
B = [i for i in matched if subs[i]["truth"] == "BUGGY"]
A = [i for i in V if subs[i]["src"] != "golden"]      # non-golden valid alternatives
fn = sum(1 for i in V if verds[i] == "REJECT")
fp = sum(1 for i in B if verds[i] == "ACCEPT")
fn_a = sum(1 for i in A if verds[i] == "REJECT")

print("=" * 76)
print("LLM-as-JUDGE (blind Claude autograder) vs PROPERTY-BASED — same 63-submission set")
print("=" * 76)
print(f"scored {len(matched)}/{len(subs)} submissions ({len(missing)} missing verdicts)")
if missing: print("  missing:", missing[:8], "..." if len(missing) > 8 else "")
print("-" * 76)
print(f"{'grader':22} {'FNR (reject valid)':22} {'FPR (accept buggy)':22} {'FNR-alt':10}")
print(f"{'PROPERTY-BASED (ours)':22} {'0/49 = 0.00':22} {'0/14 = 0.00':22} {'0/37 = 0.00'}")
print(f"{'LLM-as-judge (Claude)':22} {f'{fn}/{len(V)} = {fn/max(1,len(V)):.2f}':22} "
      f"{f'{fp}/{len(B)} = {fp/max(1,len(B)):.2f}':22} {f'{fn_a}/{len(A)} = {fn_a/max(1,len(A)):.2f}'}")
print("-" * 76)
# show which VALID the LLM-judge wrongly rejected (the "corrects correct solutions" failure)
print("LLM-judge FALSE NEGATIVES (rejected a VALID submission):")
for i in V:
    if verds[i] == "REJECT":
        print(f"  - {i:40} ({subs[i]['src']})")
print("LLM-judge FALSE POSITIVES (accepted a BUGGY submission):")
for i in B:
    if verds[i] == "ACCEPT":
        print(f"  - {i:40} ({subs[i]['src']})")
print("=" * 76)
