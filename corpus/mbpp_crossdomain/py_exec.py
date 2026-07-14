# -*- coding: utf-8 -*-
"""Python execution 'property test' — the analog of the Verilog property TB.
Runs a candidate solution against a problem's assert-based test_list in an
isolated subprocess with a wall-clock timeout. Returns 'PASS' iff all asserts
hold, else 'FAIL'/'ERROR'/'TIMEOUT'. This is the executing backbone for Python.
"""
import subprocess, tempfile, os, textwrap
def run_tests(code, setup, tests, timeout=6):
    prog = (setup or "") + "\n" + code + "\n" + "\n".join(tests) + "\nprint('___PASS___')\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(prog); path=f.name
    try:
        r = subprocess.run(["python3","-I",path], capture_output=True, text=True, timeout=timeout,
                           env={"PATH":os.environ.get("PATH","")})
        if "___PASS___" in r.stdout: return "PASS"
        return "FAIL"   # assertion failed or exception before the marker
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    finally:
        os.unlink(path)
