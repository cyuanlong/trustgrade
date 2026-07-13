#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publication figures for the TrustGrade manuscript (CAEAI style):
clean white bg, Okabe-Ito palette, Wilson-CI error bars, self-contained captions in text."""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams.update({
    "font.family": "Helvetica", "font.size": 9.5, "axes.spines.top": False,
    "axes.spines.right": False, "figure.dpi": 300, "savefig.bbox": "tight"})
OI = {"blue":"#0072B2","orange":"#E69F00","green":"#009E73","red":"#D55E00",
      "purple":"#CC79A7","sky":"#56B4E9","yellow":"#F0E442","grey":"#999999"}

def wilson(k,n,z=1.959964):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)
def err(k,n):
    lo,hi=wilson(k,n); p=k/n; return p, max(0.0,p-lo), max(0.0,hi-p)

def save(fig,name):
    fig.savefig(f"figures/{name}.png"); fig.savefig(f"figures/{name}.pdf"); plt.close(fig)
    print("saved", name)

# ---------------- Fig 1: system architecture ----------------
fig,ax=plt.subplots(figsize=(7.2,4.0)); ax.axis("off"); ax.set_xlim(0,100); ax.set_ylim(0,60)
def box(x,y,w,h,label,fc="#FFFFFF",ec="#333333",fs=8.5,lw=1.2,style="round,pad=0.35"):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=style,fc=fc,ec=ec,lw=lw))
    ax.text(x+w/2,y+h/2,label,ha="center",va="center",fontsize=fs)
def arrow(x1,y1,x2,y2,label=None,color="#333333",ls="-",fs=7.5,off=(0,1.2)):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=11,color=color,lw=1.2,linestyle=ls))
    if label: ax.text((x1+x2)/2+off[0],(y1+y2)/2+off[1],label,ha="center",fontsize=fs,color=color)
# student input
box(1,40,15,9,"Student\nsubmission",fc="#EFEFEF")
# backbone
box(24,48,14,8,"L0 Compile",fc="#DCEBF7"); box(42,48,17,8,"L1 Property\ntestbenches",fc="#DCEBF7")
box(63,48,17,8,"L2 Differential\nvs. reference",fc="#DCEBF7")
ax.text(52,58.5,"Assessment backbone (deterministic, executing)",fontsize=9,style="italic",ha="center")
arrow(16,45,24,51.5); arrow(38,52,42,52); arrow(59,52,63,52)
# verdict outputs
box(83,48.5,16.5,8,"Verifier-backed\nverdict + diagnosis",fc="#D5EEDD",fs=7.4)
arrow(80,52,83,52)
box(83,37,16.5,7.5,"UNCERTAIN (4%)\nescalate to LLM/human",fc="#FDEBD3",fs=7.2)
arrow(71,48,88,45,color="#B26A00",ls="--")
# LLM + gate
box(24,22,17,8,"LLM tutor\nexplanation + fix",fc="#F5E1EC")
box(48,22,22,8,"Feedback gate\nC1 verdict-consistency\nC2 fix passes L0-L2",fc="#DCEBF7",fs=7.8)
box(78,22,21.5,7.5,"Deliver full feedback\n(verified)",fc="#D5EEDD",fs=7.6)
box(78,10.5,21.5,8,"Fallback: verifier-only\nverdict + diagnosis\n(never rewrites)",fc="#FDEBD3",fs=7.2)
arrow(41,26,48,26); arrow(70,27,78,25.8,label="pass",fs=7.5); arrow(70,24,78,15,label="fail",fs=7.5,off=(-1.5,-1.5))
arrow(8,40,8,26); arrow(8,26,24,26)
arrow(52,48,55,30,label="backbone verdict",fs=7,off=(9,2))
# scaffold
box(1,2,20,8,"LLM scaffold generator\n(steps + hints + checkpoints)",fc="#F5E1EC",fs=7.6)
box(28,2,24,8,"Scaffold validator\ns1-s2 checkpoint passes\ns3 final step meets contract",fc="#DCEBF7",fs=7.4)
box(59,3,14,6,"Deliver step",fc="#D5EEDD",fs=8)
arrow(21,6,28,6); arrow(52,6,59,6,label="all pass",fs=7,off=(0,2.0))
save(fig,"fig1_architecture")

# ---------------- Fig 2: grader comparison, FNR/FPR with CIs ----------------
graders=["Property\n(ours)","Reference\noutput match","Token\nsimilarity","Structural\nsimilarity"]
fnr=[(0,137),(1,137),(17,137),(2,137)]; fpr=[(9,84),(11,84),(82,84),(81,84)]
fig,ax=plt.subplots(figsize=(6.4,3.2))
import numpy as np
x=np.arange(4); w=0.38
for i,(data,lab,col) in enumerate([(fnr,"FNR — rejects valid work (unfair)",OI["blue"]),
                                   (fpr,"FPR — accepts buggy work (unsafe)",OI["red"])]):
    vals=[err(k,n) for k,n in data]
    ax.bar(x+(i-0.5)*w,[v[0] for v in vals],w,color=col,alpha=0.88,label=lab,
           yerr=[[v[1] for v in vals],[v[2] for v in vals]],capsize=3,error_kw=dict(lw=1))
ax.set_xticks(x); ax.set_xticklabels(graders); ax.set_ylabel("Error rate")
ax.set_ylim(0,1.05); ax.legend(frameon=False,loc="upper left",fontsize=8.5)
for xi,(k,n) in zip(x,fpr):
    ax.text(xi+w/2,k/n+0.06,f"{k}/{n}",ha="center",fontsize=7.5,color=OI["red"])
for xi,(k,n) in zip(x,fnr):
    ax.text(xi-w/2,k/n+0.06,f"{k}/{n}",ha="center",fontsize=7.5,color=OI["blue"])
save(fig,"fig2_graders")

# ---------------- Fig 3: three-arm gate comparison ----------------
arms=["Execution gate\n(ours, ~71 ms, ≈$0)","Frontier LLM review\n(high cost)","Affordable LLM review\n(DeepSeek-chat)"]
catch=[(41,41),(41,41),(36,41)]; passv=[(28,29),(29,29),(11,29)]; harmful=[0,0,5]
fig,ax=plt.subplots(figsize=(6.4,3.2))
x=np.arange(3); w=0.38
for i,(data,lab,col) in enumerate([(catch,"Catch broken fixes (recall)",OI["green"]),
                                   (passv,"Pass valid fixes",OI["sky"])]):
    vals=[err(k,n) for k,n in data]
    ax.bar(x+(i-0.5)*w,[v[0] for v in vals],w,color=col,alpha=0.9,label=lab,
           yerr=[[v[1] for v in vals],[v[2] for v in vals]],capsize=3,error_kw=dict(lw=1))
for xi,h in zip(x,harmful):
    ax.text(xi,1.10,f"harmful delivered: {h}",ha="center",fontsize=8,
            color=(OI["red"] if h else OI["green"]),fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(arms,fontsize=8.5); ax.set_ylabel("Proportion")
ax.set_ylim(0,1.25)
ax.legend(frameon=False,loc="upper center",bbox_to_anchor=(0.5,1.17),ncol=2,fontsize=8.5)
ax.text(2,1.045,"McNemar vs. execution gate: overall p = 4.8e-7",ha="center",fontsize=7,style="italic")
save(fig,"fig3_three_arm")

# ---------------- Fig 4: gate stress interception ----------------
modes=["Authentic\ntutor (35)","Verdict flips\n(35)","Lazy fixes\n(35)","Broken fixes\n(6)","Behavior-\npreserving (29)"]
inter=[(1,35),(35,35),(35,35),(6,6),(1,29)]
correct_action=[34/35,1,1,1,28/29]
fig,ax=plt.subplots(figsize=(6.4,3.0))
cols=[OI["grey"],OI["red"],OI["red"],OI["red"],OI["grey"]]
vals=[err(k,n) for k,n in inter]
ax.bar(range(5),[v[0] for v in vals],0.62,color=cols,alpha=0.85,
       yerr=[[v[1] for v in vals],[v[2] for v in vals]],capsize=3,error_kw=dict(lw=1))
ax.set_xticks(range(5)); ax.set_xticklabels(modes,fontsize=8)
ax.set_ylabel("Interception rate"); ax.set_ylim(0,1.15)
for i,(k,n) in enumerate(inter): ax.text(i,k/n+0.05,f"{k}/{n}",ha="center",fontsize=8)
ax.text(2,-0.32,"red = faulty-tutor modes (interception is desired);  grey = legitimate content (low interception is desired)",
        ha="center",fontsize=7.5,style="italic",transform=ax.get_xaxis_transform())
save(fig,"fig4_gate_stress")

# ---------------- Fig 5: diagnosis actionability ----------------
cls=[("Named failing check",38),("Observable mismatch (with values)",13),
     ("Named behavioral invariant",9),("Generic (timeout etc.)",8),("Compiler line",7)]
fig,ax=plt.subplots(figsize=(6.0,2.6))
labels=[c for c,_ in cls][::-1]; vals=[v for _,v in cls][::-1]
cols=[OI["grey"] if "Generic" in l else OI["blue"] for l in labels]
ax.barh(labels,vals,color=cols,alpha=0.88)
for i,v in enumerate(vals): ax.text(v+0.5,i,f"{v} ({v/75:.0%})",va="center",fontsize=8)
ax.set_xlabel("Sound rejections (n = 75)"); ax.set_xlim(0,46)
ax.set_title("89% of rejections carry an actionable named signal",fontsize=9.5,loc="left")
save(fig,"fig5_diagnosis")

# ---------------- Fig 6: ground-truth construction pipeline ----------------
fig,ax=plt.subplots(figsize=(7.2,3.4)); ax.axis("off"); ax.set_xlim(0,100); ax.set_ylim(0,52)
box(1,36,20,10,"37 objectives\nspec + interface +\nreference + property TB",fc="#EFEFEF",fs=7.6)
box(29,42,28,8,"Semantics-preserving variants\n(machine-verified alpha-equivalence)",fc="#DCEBF7",fs=7.0)
box(30,31,26,8,"Algorithmically distinct\nverified solutions",fc="#DCEBF7",fs=7.6)
box(30,17,26,8,"Mutation injection\n(operators, constants, timing)",fc="#FBE3D5",fs=7.6)
box(30,6,26,8,"Instructor-authored\nrealistic bugs",fc="#FBE3D5",fs=7.6)
box(65,36,15.5,9,"137 VALID\n(101 alternatives)",fc="#D5EEDD",fs=7.6)
box(65,12,15.5,9,"84 BUGGY\n(oracle-confirmed)",fc="#F8D7D0",fs=7.6)
box(86,24,13,9,"221-item\ncorpus",fc="#EFEFEF",fs=8.5)
arrow(21,42,30,45.5); arrow(21,40,30,35); arrow(21,38,30,22); arrow(21,37,30,10)
arrow(56,46,66,42); arrow(56,35,66,40)
arrow(56,21,60,20,label=None); arrow(56,10,60,15)
box(57,14.5,7.5,6,"2-seed\ndiff oracle",fc="#FFF6DA",fs=6.4,style="round,pad=0.2")
arrow(64.5,17.5,66,17)
arrow(80,40,86,30); arrow(80,16,86,26)
save(fig,"fig6_corpus")

# ---------------- Fig 7: worked example (panel figure) ----------------
fig,ax=plt.subplots(figsize=(7.2,4.6)); ax.axis("off"); ax.set_xlim(0,100); ax.set_ylim(0,66)
def panel(x,y,w,h,title,body,fc,fs=7.0):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.4",fc=fc,ec="#444444",lw=1))
    ax.text(x+1.2,y+h-2.2,title,fontsize=8,fontweight="bold",va="top")
    ax.text(x+1.2,y+h-6.5,body,fontsize=fs,va="top",family="Menlo")
panel(1,42,47,22,"(a) Student submission (round-robin arbiter, excerpt)",
"always @(posedge clk) begin\n  if (!rst_n) base <= 2'd0;\n  else if (gvalid)\n    base <= gidx;      // keeps served\nend                    // line highest-prio",
"#FFFFFF")
panel(52,42,47,22,"(b) Backbone verdict (L1 property testbench)",
"VERDICT: REJECT  (verifier-backed)\nVIOLATION starvation: req[2]\n  unserved for 5 cycles\n  (req=0101 ...)   [corpus-verbatim]",
"#F8D7D0")
panel(1,14,47,24,"(c) LLM tutor message (pre-gate)",
"verdict: BUGGY\nexplanation: pointer must advance PAST\n  the served index, or that requester\n  keeps top priority and others starve\ncorrected_rtl: base <= gidx + 2'd1; ...",
"#FFFFFF")
panel(52,14,47,24,"(d) Gate checks -> delivery",
"C1 verdict-consistency ..... PASS\nC2 fix passes L0+L1+L2 ..... PASS\n    (compile OK; P1-P3 hold;\n     matches reference behavior)\n=> DELIVER explanation + verified fix\n   [71 ms, $0]",
"#D5EEDD")
ax.text(1,7,"If C1 or C2 fails: the LLM text is withheld and the student receives the verifier-backed diagnosis in (b) —\nharmful feedback cannot reach the learner (76/76 intercepted in stress tests).",fontsize=8,style="italic",va="top")
save(fig,"fig7_worked_example")
print("ALL FIGURES DONE")
