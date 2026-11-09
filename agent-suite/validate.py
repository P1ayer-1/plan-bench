#!/usr/bin/env python3
"""Sanity-check the task suite: every task must FAIL on the untouched sandbox
and PASS once its reference solution is applied. Run this after editing tasks."""
import shutil, sys, tempfile
from pathlib import Path
from grading import grade

ROOT = Path(__file__).parent
ok = True
for task in sorted((ROOT / "tasks").iterdir()):
    if not task.is_dir():
        continue
    results = {}
    for mode in ("base", "ref"):
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d) / "ws"
            shutil.copytree(ROOT / "sandbox", ws)
            if mode == "ref":
                shutil.copytree(ROOT / "validation" / "refs" / task.name, ws, dirs_exist_ok=True)
            results[mode] = grade(task, ws, timeout=30 if mode == "base" else 180)
    good = (not results["base"]["passed"]) and results["ref"]["passed"] and results["ref"]["visible_passed"]
    ok &= good
    print(f"{'OK ' if good else 'BAD'} {task.name:22} base_passed={results['base']['passed']}  "
          f"ref_passed={results['ref']['passed']}  ref_visible={results['ref']['visible_passed']}")
    if not good:
        print("   ", results["ref"]["detail"][-600:].replace("\n", "\n    "))
sys.exit(0 if ok else 1)
