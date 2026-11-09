import subprocess, sys

CSV = """date,description,amount,category,tags
2026-01-03,Coffee,-4.50,food,
2026-01-15,Salary,3000.00,income,
2026-02-01,Rent,-1200.00,housing,
2026-02-10,Lunch,-12.25,food,
"""

def run(tmp_path, *args):
    f = tmp_path / "x.csv"; f.write_text(CSV)
    return subprocess.run([sys.executable, "-m", "ledger.cli", *[a.replace("FILE", str(f)) for a in args]],
                          capture_output=True, text=True)

def test_all(tmp_path):
    assert run(tmp_path, "balance", "FILE").stdout.strip() == "Balance: 1783.25 USD"

def test_since_category(tmp_path):
    assert run(tmp_path, "balance", "FILE", "--since", "2026-01-04", "--category", "food").stdout.strip() == "Balance: -12.25 USD"

def test_until_inclusive(tmp_path):
    assert run(tmp_path, "balance", "FILE", "--until", "2026-01-15").stdout.strip() == "Balance: 2995.50 USD"

def test_empty(tmp_path):
    assert run(tmp_path, "balance", "FILE", "--category", "nope").stdout.strip() == "Balance: 0.00 USD"

def test_bad_date(tmp_path):
    r = run(tmp_path, "balance", "FILE", "--since", "2026-13-01")
    assert r.returncode == 2 and r.stderr.strip()

def test_summary_still_works(tmp_path):
    r = run(tmp_path, "summary", "FILE")
    assert r.returncode == 0 and "2026-02" in r.stdout
