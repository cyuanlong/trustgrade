#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paper-A vertical slice (P1 exit evidence).

Question: does PROPERTY-BASED grading accept the whole space of valid solutions
while incumbent REFERENCE-MATCHING graders falsely reject structurally-different
valid solutions?

Dataset: arb_bundle.json = 1 property TB + 3 structurally-diverse CORRECT
round-robin arbiters (pointer / mask / counter) + 2 BROKEN arbiters.

Graders compared on the same 5 submissions:
  PROP      (proposed)  : run the property TB (P1 mutex / P2 no-empty / P3 fairness).
                          ACCEPT iff all invariants hold.
  REF-OUT   (baseline)  : pick correct[0] as the single reference; build its golden
                          grant trace; ACCEPT iff candidate's grant trace == golden.
  TEXT-SIM  (baseline)  : token Jaccard similarity of candidate RTL vs reference RTL;
                          ACCEPT iff sim >= THRESH.

Headline metric: FALSE-NEGATIVE rate on valid alternative solutions
(the correct[1..] that differ from the reference). Lower = fairer grader.

CPU-only (iverilog/vvp). Self-contained in edu_pivot. Touches nothing else.
"""
import json, subprocess, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE = os.path.join(HERE, "arb_bundle.json")
WORK = os.path.join(HERE, "_run")
os.makedirs(WORK, exist_ok=True)
TEXT_SIM_THRESH = 0.60

bundle = json.load(open(BUNDLE))
PROP_TB = bundle["property_tb"]

def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=90)

def compile_run(files, top, tag):
    d = os.path.join(WORK, tag); os.makedirs(d, exist_ok=True)
    names = []
    for n, c in files.items():
        open(os.path.join(d, n), "w").write(c); names.append(n)
    c = sh(["iverilog", "-g2012", "-s", top, "-o", "sim.vvp"] + names, d)
    if c.returncode != 0:
        return None, "COMPILE_ERROR: " + c.stderr.strip().splitlines()[-1][:120] if c.stderr.strip() else "COMPILE_ERROR"
    r = sh(["vvp", "sim.vvp"], d)
    return r.stdout, None

# ---- trace TB for the reference-output-matching baseline ----
TRACE_TB = r"""
`timescale 1ns/1ps
module trace_tb;
  reg clk, rst_n; reg [3:0] req; wire [3:0] grant; integer i;
  reg [3:0] stim [0:19];
  arbiter_rr dut(.clk(clk), .rst_n(rst_n), .req(req), .grant(grant));
  initial clk = 0; always #5 clk = ~clk;
  initial begin
    stim[0]=4'b1111; stim[1]=4'b1111; stim[2]=4'b1111; stim[3]=4'b1111;
    stim[4]=4'b1010; stim[5]=4'b1010; stim[6]=4'b0110; stim[7]=4'b0110;
    stim[8]=4'b1001; stim[9]=4'b1001; stim[10]=4'b1111; stim[11]=4'b0011;
    stim[12]=4'b1100; stim[13]=4'b1111; stim[14]=4'b0001; stim[15]=4'b1000;
    stim[16]=4'b0111; stim[17]=4'b1110; stim[18]=4'b0101; stim[19]=4'b1011;
    rst_n=0; req=0; @(posedge clk); @(posedge clk); rst_n=1;
    for (i=0;i<20;i=i+1) begin
      req=stim[i]; @(posedge clk); #1;
      $display("CYC %0d req=%b grant=%b", i, req, grant);
    end
    $finish;
  end
  initial begin #100000; $display("TIMEOUT"); $finish; end
endmodule
"""

def tokenize(rtl):
    # strip comments, then word/symbol tokens
    rtl = re.sub(r"//[^\n]*", " ", rtl)
    rtl = re.sub(r"/\*.*?\*/", " ", rtl, flags=re.S)
    return set(re.findall(r"[A-Za-z_]\w*|[^\s\w]", rtl))

def grade_prop(c):
    out, err = compile_run({"dut.v": c["rtl"], "ptb.v": PROP_TB}, "property_tb", "prop_" + c["name"])
    if err: return "ERROR", err
    ok = ("PASSED" in out) and ("FAILED" not in out)
    last = (out.strip().splitlines() or ["(no output)"])[-1]
    return ("ACCEPT" if ok else "REJECT"), last[:90]

def trace_of(c, tag):
    out, err = compile_run({"dut.v": c["rtl"], "ttb.v": TRACE_TB}, "trace_tb", "trace_" + tag)
    if err: return None
    return [l for l in out.splitlines() if l.startswith("CYC")]

def main():
    correct = bundle["correct"]; broken = bundle["broken"]
    ref = correct[0]
    ref_tokens = tokenize(ref["rtl"])
    golden = trace_of(ref, "REF")
    submissions = [("correct", c) for c in correct] + [("broken", b) for b in broken]

    rows = []
    for kind, c in submissions:
        gold_label = "VALID" if kind == "correct" else "BUGGY"
        # PROP
        prop_v, prop_msg = grade_prop(c)
        # REF-OUT
        tr = trace_of(c, c["name"])
        ref_v = "ACCEPT" if (tr is not None and tr == golden) else "REJECT"
        # TEXT-SIM
        tk = tokenize(c["rtl"])
        sim = len(tk & ref_tokens) / max(1, len(tk | ref_tokens))
        txt_v = "ACCEPT" if sim >= TEXT_SIM_THRESH else "REJECT"
        rows.append(dict(name=c["name"], gold=gold_label, prop=prop_v, refout=ref_v,
                         textsim=txt_v, sim=round(sim, 2), prop_msg=prop_msg))

    # ---- report ----
    print("=" * 92)
    print("PAPER-A VERTICAL SLICE  —  property-based grading vs reference-matching")
    print("=" * 92)
    hdr = f"{'submission':24} {'truth':6} | {'PROP':7} {'REF-OUT':8} {'TEXT-SIM':9} (sim)"
    print(hdr); print("-" * 92)
    for r in rows:
        print(f"{r['name']:24} {r['gold']:6} | {r['prop']:7} {r['refout']:8} {r['textsim']:9} ({r['sim']})")
    print("-" * 92)

    def conf(rows, grader):
        # confusion vs ground truth
        fn = sum(1 for r in rows if r["gold"] == "VALID"  and r[grader] == "REJECT")  # false neg (kill valid)
        tp = sum(1 for r in rows if r["gold"] == "VALID"  and r[grader] == "ACCEPT")
        tn = sum(1 for r in rows if r["gold"] == "BUGGY"  and r[grader] == "REJECT")
        fp = sum(1 for r in rows if r["gold"] == "BUGGY"  and r[grader] == "ACCEPT")  # false pos (pass buggy)
        nvalid = tp + fn
        # false-neg rate among VALID-but-NON-reference (the alternatives) — headline
        alts = [r for r in rows if r["gold"] == "VALID" and r["name"] != rows[0]["name"]]
        fn_alt = sum(1 for r in alts if r[grader] == "REJECT")
        return dict(fn=fn, tp=tp, tn=tn, fp=fp, nvalid=nvalid,
                    fnr=round(fn / max(1, nvalid), 2),
                    fnr_alt=round(fn_alt / max(1, len(alts)), 2))

    print("METRICS (truth: 3 VALID incl. reference, 2 BUGGY)")
    print(f"{'grader':9} | {'accept-valid':12} {'reject-buggy':12} {'FN(kill valid)':15} {'FNR':5} {'FNR-on-alternatives':20}")
    for g, label in [("prop", "PROP"), ("refout", "REF-OUT"), ("textsim", "TEXT-SIM")]:
        m = conf(rows, g)
        print(f"{label:9} | {str(m['tp'])+'/'+str(m['nvalid']):12} {str(m['tn'])+'/2':12} "
              f"{m['fn']:<15} {m['fnr']:<5} {m['fnr_alt']}")
    print("=" * 92)
    print("Expected headline: PROP accepts all 3 valid & rejects both buggy (FNR=0);")
    print("REF-OUT / TEXT-SIM falsely reject the structurally-different valid solutions (FNR>0).")

if __name__ == "__main__":
    main()
