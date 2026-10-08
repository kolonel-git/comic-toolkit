"""Run every test script in this folder, each in its own process, and report pass or fail.

    python tests/run_all.py            all of them
    python tests/run_all.py order      only the scripts whose name contains "order"

Each script is a plain program that asserts and prints a final "... OK" line; it passes when it exits with code 0.
The window tests open real (briefly visible) windows, so run them on a desktop session and leave the mouse alone.
"""
import subprocess
import sys
import time
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parent
pick = sys.argv[1] if len(sys.argv) > 1 else ""
scripts = sorted(p for p in here.glob("test_*.py") if pick in p.name)
failed = []
for p in scripts:
    t0 = time.time()
    r = subprocess.run([sys.executable, "-W", "error::SyntaxWarning", str(p)], cwd=root, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    ok = r.returncode == 0
    print(f"{'PASS' if ok else 'FAIL'}  {p.name:24} {time.time() - t0:5.1f}s")
    if not ok:
        failed.append(p.name)
        print("      " + "\n      ".join((r.stderr or r.stdout).strip().splitlines()[-6:]))
print(f"\n{len(scripts) - len(failed)} of {len(scripts)} passed")
sys.exit(1 if failed else 0)
