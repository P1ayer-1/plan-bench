"""Grade t05: agent's tests must pass on the real report.py and fail on most mutants."""
import os, shutil, subprocess, sys
from pathlib import Path

ws = Path(sys.argv[1])
test = ws / "tests" / "test_report.py"
report = ws / "ledger" / "report.py"
if not test.exists():
    print("no tests/test_report.py"); sys.exit(1)
original = report.read_text()

MUTANTS = [
    ('f"{tx.date.year:04d}-{tx.date.month:02d}"', 'f"{tx.date.year:04d}-{tx.date.day:02d}"'),
    ("return dict(sorted(result.items()))", "return dict(result.items())"),
    ("tx.amount.amount < 0]", "tx.amount.amount <= 0]"),
    ("key=lambda tx: tx.amount.amount)[:n]", "key=lambda tx: tx.amount.amount)[:n-1]"),
    ("key=lambda tx: tx.amount.amount)[:n]", "key=lambda tx: -tx.amount.amount)[:n]"),
    ("result[m][tx.category] + tx.amount", "result[m][tx.category] - tx.amount"),
]

ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

def run():
    for c in ws.rglob("__pycache__"):
        shutil.rmtree(c, ignore_errors=True)  # stale .pyc would hide same-size mutants
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", str(test)],
                       cwd=ws, capture_output=True, text=True, timeout=120, env=ENV)
    return p.returncode == 0

try:
    if not run():
        print("tests fail on original code"); sys.exit(1)
    killed = 0
    for old, new in MUTANTS:
        assert old in original, old
        report.write_text(original.replace(old, new, 1))
        if not run():
            killed += 1
    print(f"killed {killed}/{len(MUTANTS)} mutants")
    sys.exit(0 if killed >= 5 else 1)
finally:
    report.write_text(original)
    for c in ws.rglob("__pycache__"):
        shutil.rmtree(c, ignore_errors=True)
