import json, sys, difflib
sys.path.insert(0, ".")
import corpus_run as C
objs = {o["name"]: o for o in C.build_corpus()}
rows = json.load(open("corpus_results.json"))
seen = set()
print("=== PROP-accepted buggy: what the injection changed (golden vs mutant) ===")
for r in rows:
    if r["truth"] == "BUGGY" and r["prop"] == "ACCEPT":
        o = objs[r["obj"]]
        mut = [rtl for src, rtl in o["buggys"] if src == r["src"]]
        key = (r["obj"], r["src"])
        if key in seen or not mut:
            continue
        seen.add(key)
        dif = [l for l in difflib.unified_diff(o["golden"].splitlines(), mut[0].splitlines(), lineterm="", n=0)
               if l[:1] in "+-" and l[:2] not in ("++", "--")]
        change = " || ".join(dif[:2])[:110]
        print("- {:16} {:16} REFOUT={:7} | {}".format(r["obj"], r["src"], r["refout"], change))
