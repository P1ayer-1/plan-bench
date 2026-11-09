import time
from datetime import date, timedelta
from ledger import Money, Ledger, Transaction

def test_semantics():
    d = date(2026,1,1)
    a = Transaction(d, "x", Money("1"), "c", ("t",))
    b = Transaction(d, "x", Money("1"), "other")      # dup of a (category/tags ignored)
    c = Transaction(d, "x", Money("2"), "c")
    l = Ledger([a, c, b, a]).dedupe()
    assert l.transactions == [a, c]
    assert isinstance(l, Ledger)

def test_speed():
    base = date(2020,1,1)
    txs = [Transaction(base + timedelta(days=i % 1500), f"d{i % 50000}", Money(i % 97), "c") for i in range(200_000)]
    l = Ledger(txs)
    t0 = time.perf_counter(); l.dedupe(); dt = time.perf_counter() - t0
    assert dt < 2.0, dt
    keys = [(t.date, t.description, t.amount) for t in l.transactions]
    assert len(keys) == len(set(keys))
