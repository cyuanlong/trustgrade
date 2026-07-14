# -*- coding: utf-8 -*-
"""Construction-based ground truth on MBPP (Python analog of the Verilog corpus).
VALID  = reference solution + a semantics-preserving reformat variant (tests pass).
BUGGY  = AST-mutation-injected versions, oracle-confirmed by the test_list FAILING.
Graders/arms judge byte-identical candidate code."""
import json, ast, random, copy, re
from py_exec import run_tests
random.seed(7)

# ---- AST mutation operators ----
class Mut(ast.NodeTransformer):
    def __init__(self, kind): self.kind=kind; self.done=False
    def _once(self): 
        if self.done: return False
        self.done=True; return True
    def visit_BinOp(self,n):
        self.generic_visit(n)
        if self.kind=="arith" and isinstance(n.op,(ast.Add,ast.Sub)) and self._once():
            n.op=ast.Sub() if isinstance(n.op,ast.Add) else ast.Add()
        elif self.kind=="muldiv" and isinstance(n.op,(ast.Mult,ast.FloorDiv,ast.Div)) and self._once():
            n.op=ast.Add()
        return n
    def visit_Compare(self,n):
        self.generic_visit(n)
        if self.kind=="cmp" and self._once() and n.ops:
            m={ast.Lt:ast.LtE,ast.LtE:ast.Lt,ast.Gt:ast.GtE,ast.GtE:ast.Gt,ast.Eq:ast.NotEq,ast.NotEq:ast.Eq}
            t=type(n.ops[0])
            if t in m: n.ops[0]=m[t]()
        return n
    def visit_BoolOp(self,n):
        self.generic_visit(n)
        if self.kind=="bool" and self._once():
            n.op=ast.Or() if isinstance(n.op,ast.And) else ast.And()
        return n
    def visit_Constant(self,n):
        if self.kind=="const" and isinstance(n.value,int) and not isinstance(n.value,bool) and self._once():
            n.value=n.value+1
        return n

def mutate(code, kind):
    try:
        tree=ast.parse(code); m=Mut(kind); nt=m.visit(copy.deepcopy(tree))
        if not m.done: return None
        ast.fix_missing_locations(nt); return ast.unparse(nt)
    except Exception: return None

def reformat(code):
    # semantics-preserving: strip comments + normalize via ast roundtrip
    try: return ast.unparse(ast.parse(code))
    except Exception: return None

rows=json.load(open("mbpp_all.json"))
random.shuffle(rows)
items=[]; used=0
for r in rows:
    if used>=150: break
    setup=r.get("test_setup_code",""); tests=r["test_list"]; code=r["code"]
    if run_tests(code,setup,tests)!="PASS": continue
    used+=1
    tid=r["task_id"]; spec=r["text"]
    # VALID: reference + reformat variant (must still pass)
    items.append(dict(id=f"{tid}__golden",tid=tid,spec=spec,code=code,truth="OK",setup=setup,tests=tests))
    rf=reformat(code)
    if rf and rf.strip()!=code.strip() and run_tests(rf,setup,tests)=="PASS":
        items.append(dict(id=f"{tid}__reformat",tid=tid,spec=spec,code=rf,truth="OK",setup=setup,tests=tests))
    # BUGGY: first 2 oracle-confirmed mutants across operators
    nb=0
    for kind in ["arith","cmp","const","bool","muldiv"]:
        if nb>=2: break
        mut=mutate(code,kind)
        if mut and mut.strip()!=code.strip() and run_tests(mut,setup,tests)=="FAIL":
            items.append(dict(id=f"{tid}__mut_{kind}",tid=tid,spec=spec,code=mut,truth="BROKEN",setup=setup,tests=tests)); nb+=1
json.dump(items,open("mbpp_items.json","w"))
ok=sum(1 for i in items if i["truth"]=="OK"); br=len(items)-ok
print(f"MBPP corpus: {used} problems -> {len(items)} candidates (OK={ok}, BROKEN={br})")
