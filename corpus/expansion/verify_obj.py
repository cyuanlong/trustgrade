# -*- coding: utf-8 -*-
"""verify_obj.py <objects.json> — check each objective end-to-end with iverilog.
An objective = {name, interface, golden_rtl, property_tb, buggy_rtl}. Prints, per
objective: golden->PASS? buggy->FAIL? and an overall OK/BAD. Only OK objectives
should be kept."""
import json, sys, os, subprocess, tempfile, re
def run(files, top, tmo=8):
    d=tempfile.mkdtemp()
    ns=[]
    for n,c in files.items():
        open(os.path.join(d,n),"w").write(c); ns.append(n)
    c=subprocess.run(["iverilog","-g2012","-s",top,"-o","s.vvp"]+ns,cwd=d,capture_output=True,text=True)
    if c.returncode!=0: return None,"COMPILE:"+(c.stderr.strip().splitlines() or [""])[-1][:80]
    try: r=subprocess.run(["vvp","s.vvp"],cwd=d,capture_output=True,text=True,timeout=tmo)
    except subprocess.TimeoutExpired: return None,"HANG"
    return r.stdout,None
def tbtop(tb):
    m=re.search(r"\bmodule\s+(\w+)",tb); return m.group(1) if m else "tb"
FAIL=re.compile(r"\bFAIL|VIOLATION|MISMATCH|GLITCH|TIMEOUT|STARV")
def verdict(rtl,tb):
    out,err=run({"dut.v":rtl,"ptb.v":tb},tbtop(tb))
    if err: return "REJECT",err
    return ("ACCEPT" if ("PASS" in out and not FAIL.search(out)) else "REJECT"), (out.strip().splitlines() or [""])[-1][:70]
objs=json.load(open(sys.argv[1]))
ok=0
for o in objs:
    gv,gm=verdict(o["golden_rtl"],o["property_tb"])
    bv,bm=verdict(o["buggy_rtl"],o["property_tb"])
    good = (gv=="ACCEPT" and bv=="REJECT")
    ok += good
    print(f"[{'OK ' if good else 'BAD'}] {o['name']:24} golden->{gv:7}({gm[:30]})  buggy->{bv:7}({bm[:30]})")
print(f"\n{ok}/{len(objs)} objectives valid")
