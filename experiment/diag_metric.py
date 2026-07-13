#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paper-A formative-feedback metric (misconception diagnosis).
A property/tool-based grader does not just say pass/fail; it localizes the
misconception. We quantify that: map each buggy submission's tool output to a
bug_catalog category via tool_signature, and score vs the ground-truth bug_type.

Uses D9 (1167 buggy samples, ground-truth bug_type) + bug_catalog (signatures).
Pure string processing (no simulation). Read-only on the workspace.
"""
import json, os, re, collections

WS = "/root/autodl-tmp/eda_workspace"
catalog = json.load(open(os.path.join(WS, "D9_error_diagnosis/bug_catalog.json")))
SIG = {bt: info.get("tool_signature", "") for bt, info in catalog.items()}
# generic / non-discriminative signatures we flag (substring would match almost anything)
GENERIC = {bt for bt, s in SIG.items() if s.lower() in ("warning", "error", "")}

def diagnose(tool_output):
    """Return set of bug categories whose tool_signature appears in the tool output."""
    t = (tool_output or "").lower()
    return {bt for bt, s in SIG.items() if s and bt not in GENERIC and s.lower() in t}

rows = []
for l in open(os.path.join(WS, "D9_error_diagnosis/samples.jsonl")):
    try: r = json.loads(l)
    except: continue
    gt = r.get("bug_type")
    if gt is None: continue
    pred = diagnose(r.get("tool_output", ""))
    rows.append((gt, pred))

N = len(rows)
cov = sum(1 for gt, p in rows if p)                              # any signature matched
inset = sum(1 for gt, p in rows if gt in p)                      # ground-truth among matches
unique = sum(1 for gt, p in rows if p == {gt})                   # exactly & only ground-truth
print("=" * 84)
print("PAPER-A FORMATIVE-FEEDBACK METRIC — misconception diagnosis via tool signatures")
print("=" * 84)
print(f"samples N = {N}   bug categories = {len(SIG)}   (non-discriminative sigs excluded: {sorted(GENERIC)})")
print(f"diagnosable (any signature fired)      : {cov}/{N} = {cov/N:.2f}")
print(f"in-set accuracy  (GT among matches)    : {inset}/{N} = {inset/N:.2f}")
print(f"exact accuracy   (GT is the only match): {unique}/{N} = {unique/N:.2f}")
print("-" * 84)
# per-category recall (of samples of type X, how often GT signature fired)
per = collections.defaultdict(lambda: [0, 0])
for gt, p in rows:
    per[gt][1] += 1
    if gt in p: per[gt][0] += 1
print(f"{'bug_type':22} {'recall(GT sig fired)':22} {'n':>5}   signature")
for bt in sorted(per, key=lambda b: -per[b][1]):
    hit, n = per[bt]
    tag = "  [excluded: generic]" if bt in GENERIC else ""
    print(f"{bt:22} {hit}/{n} = {hit/max(1,n):.2f}{'':6} {n:>5}   '{SIG.get(bt,'')}'{tag}")
print("=" * 84)
json.dump([{"gt": gt, "pred": sorted(p)} for gt, p in rows],
          open("/root/autodl-tmp/edu_pivot/diag_results.json", "w"), ensure_ascii=False)
print("saved diag_results.json")
