#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fig 8: application-scenario swimlane — one assignment lifecycle through the
verification-gated tutoring pipeline, with concrete data artifacts on each edge."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

plt.rcParams.update({"font.family":"Helvetica","font.size":8.5,"figure.dpi":300,"savefig.bbox":"tight"})
fig,ax=plt.subplots(figsize=(9.6,6.4)); ax.axis("off"); ax.set_xlim(0,140); ax.set_ylim(0,96)

LANES=[("Instructor",76,96,"#F4F6F8"),("Student",56,76,"#FFFFFF"),
       ("TrustGrade verifier plane\n(deterministic, executing)",26,56,"#EDF4FB"),
       ("LLM plane\n(generative, gated)",2,26,"#FBF0F6")]
for name,y0,y1,fc in LANES:
    ax.add_patch(Rectangle((6,y0),134,y1-y0,fc=fc,ec="#B9C2CC",lw=0.8))
    ax.text(5,(y0+y1)/2,name,rotation=90,ha="center",va="center",fontsize=8,fontweight="bold")

def box(x,y,w,h,label,fc="#FFFFFF",ec="#333",fs=7.4,mono=False,lw=1.1):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.3",fc=fc,ec=ec,lw=lw))
    ax.text(x+w/2,y+h/2,label,ha="center",va="center",fontsize=fs,
            family=("Menlo" if mono else plt.rcParams["font.family"]))
def arr(x1,y1,x2,y2,label=None,c="#333",fs=6.6,dx=0,dy=1.1,ls="-"):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=9,color=c,lw=1.1,linestyle=ls))
    if label: ax.text((x1+x2)/2+dx,(y1+y2)/2+dy,label,ha="center",fontsize=fs,color=c,style="italic")

# --- Instructor lane: authoring ---
box(9,81,26,11,"Author objective  $o=(\\sigma, I, r, \\Phi, H)$\nspec + interface + reference\n+ property testbench",fc="#FFFFFF",fs=7.2)
box(112,81,25,11,"Escalation queue\nUNCERTAIN cases\n(4.1% of verdicts)",fc="#FDEBD3",fs=7.2)
# --- Student lane ---
box(15,62,20,9,"Submit design  $s$\n(e.g. rr_arb4.v)",fs=7.4)
box(58,62,30,9,"Receives: verdict $V_B(s)$ +\nnamed diagnosis $\\delta(s)$\n(verifier-backed)",fc="#D5EEDD",fs=7.2)
box(96,62,28,9,"Receives: explanation +\nverified fix / Socratic step\n(gate-passed only)",fc="#D5EEDD",fs=7.2)
# --- Verifier lane ---
box(10,42,15,9,"L0 compile\niverilog",fs=7.2)
box(29,42,17,9,"L1 properties\n$s \\models \\Phi$?",fs=7.4)
box(50,42,17,9,"L2 differential\n$s \\equiv_H r$?",fs=7.4)
box(71,42,26,9,"Verdict $V_B(s)\\in$\n{ACC, REJ, UNC}\n+ diagnosis $\\delta(s)$",fc="#DCEBF7",fs=7.2)
box(103,42,34,9,"Feedback gate  $G$\nC1: $v_t = V_B(s)$   C2: $V_B(f)=$ ACC\ndeliver | withhold (never rewrite)",fc="#DCEBF7",fs=7.0)
box(29,29,38,7,'e.g. "FAILED: P3 fairness/starvation\n t=245ns  req=1001  grant=0001"',fc="#F8D7D0",fs=6.6,mono=True)
# --- LLM lane ---
box(29,8,30,10,"Tutor draft  $m=(v_t,e,f)$\nverdict + explanation\n+ corrected RTL",fc="#FFFFFF",fs=7.2)
box(70,8,30,10,"Scaffold generator\nsteps $(g_i,h_i,r_i,c_i)$\n+ self-test loop",fc="#FFFFFF",fs=7.2)
box(104,8,33,10,"Scaffold validator\n$\\forall i$: $c_i$ passes on $r_i$;\n$r_n \\models \\Phi$  (contract)",fc="#DCEBF7",fs=7.0)

# --- flows ---
arr(11,81,11,51,None)
ax.text(12.2,77.5,"objective $o$ (37 in corpus)",fontsize=6.6,style="italic",ha="left")
arr(25,66,25,51,"$s$",dx=-2)
arr(25,46.5,29,46.5); arr(46,46.5,50,46.5); arr(67,46.5,71,46.5)
arr(38,42,40,36,"$\\delta(s)$",dx=4)
arr(84,51,72,62,"REJ/ACC + $\\delta$",dx=10,dy=0)
arr(97,47,103,47,"$V_B(s)$")
arr(84,42,44,18,"verdict + diagnosis context",dx=-6,dy=-8)
ax.text(85,19.6,"invoked when the student asks where to start",fontsize=6.2,style="italic",ha="center")
arr(59,15,111,42,"$m=(v_t,e,f)$",dx=14,dy=-5)
arr(120,51,112,62,"pass",dx=3.5,dy=0)
arr(133,51,128,81,None)
ax.text(127.5,53.2,"fail C1/C2 -> fallback $(V_B,\\delta)$; UNC -> instructor",fontsize=6.0,style="italic",ha="center")
arr(120,18,120,42,"validated steps only",dx=9)
ax.text(73,93.5,"One assignment lifecycle (left -> right).  Solid boxes = artifacts; shaded = verifier-owned decisions.",
        fontsize=7.6,style="italic",ha="center")
fig.savefig("figures/fig8_scenario.png"); fig.savefig("figures/fig8_scenario.pdf")
print("saved fig8_scenario")
