from datetime import date, timedelta
import random
import time
from ledger import Money, Transaction
from ledger.reconcile import reconcile

BASE = date(2026, 3, 1)


def tx(day, amt, desc="x", cur="USD"):
    return Transaction(BASE + timedelta(days=day), desc, Money(amt, cur), "c")


def check(res, L, B, max_days=3):
    used_l, used_b = set(), set()
    for l, b in res.matched:
        assert l.amount == b.amount and abs((l.date - b.date).days) <= max_days
        assert id(l) not in used_l and id(b) not in used_b
        used_l.add(id(l)); used_b.add(id(b))
    assert [id(t) for t in res.unmatched_ledger] == [id(t) for t in L if id(t) not in used_l]
    assert [id(t) for t in res.unmatched_bank] == [id(t) for t in B if id(t) not in used_b]
    pos = {id(t): i for i, t in enumerate(L)}
    assert [pos[id(l)] for l, _ in res.matched] == sorted(pos[id(l)] for l, _ in res.matched)
    return len(res.matched), sum(abs((l.date - b.date).days) for l, b in res.matched)


def test_basic():
    L = [tx(0, "-10"), tx(5, "-20"), tx(9, "7")]
    B = [tx(1, "-10"), tx(5, "-20"), tx(20, "7")]
    assert check(reconcile(L, B), L, B) == (2, 1)


def test_currency_must_match():
    L = [tx(0, "-10", cur="USD")]
    B = [tx(0, "-10", cur="EUR")]
    assert check(reconcile(L, B), L, B) == (0, 0)


def test_max_days_boundary():
    L = [tx(0, "-5"), tx(0, "-6")]
    B = [tx(3, "-5"), tx(-4, "-6")]
    assert check(reconcile(L, B), L, B) == (1, 3)
    assert check(reconcile(L, B, max_days=4), L, B, 4) == (2, 7)


def test_greedy_closest_loses_a_pair():
    # Greedy-by-closest pairs L0 with B0 (distance 0) and then L1 has nothing within 3 days.
    L = [tx(0, "-30"), tx(-3, "-30")]
    B = [tx(0, "-30"), tx(3, "-30")]
    assert check(reconcile(L, B), L, B) == (2, 6)


def test_greedy_in_order_is_not_minimal():
    # Taking ledger items in order and grabbing their nearest bank item gives total 3; optimal is 1.
    L = [tx(1, "-9"), tx(2, "-9")]
    B = [tx(2, "-9"), tx(0, "-9")]
    assert check(reconcile(L, B), L, B) == (2, 1)
    L = [tx(0, "-9"), tx(3, "-9"), tx(6, "-9")]
    B = [tx(2, "-9"), tx(4, "-9"), tx(8, "-9")]
    assert check(reconcile(L, B), L, B) == (3, 5)


def test_duplicates_are_separate():
    L = [tx(0, "-4", "coffee"), tx(0, "-4", "coffee"), tx(0, "-4", "coffee")]
    B = [tx(1, "-4", "coffee"), tx(0, "-4", "coffee")]
    n, dist = check(reconcile(L, B), L, B)
    assert (n, dist) == (2, 1)


def brute(L, B, max_days=3):
    best = (0, 0)
    def go(i, used, n, d):
        nonlocal best
        if i == len(L):
            if n > best[0] or (n == best[0] and d < best[1]):
                best = (n, d)
            return
        go(i + 1, used, n, d)
        for j, b in enumerate(B):
            if j not in used and b.amount == L[i].amount and abs((L[i].date - b.date).days) <= max_days:
                go(i + 1, used | {j}, n + 1, d + abs((L[i].date - b.date).days))
    go(0, frozenset(), 0, 0)
    return best


def test_random_against_brute_force():
    rng = random.Random(7)
    for _ in range(150):
        L = [tx(rng.randint(0, 12), rng.choice(["-1", "-2"])) for _ in range(rng.randint(0, 6))]
        B = [tx(rng.randint(0, 12), rng.choice(["-1", "-2"])) for _ in range(rng.randint(0, 6))]
        assert check(reconcile(L, B), L, B) == brute(L, B)


def test_performance():
    rng = random.Random(1)
    amounts = [str(-(i + 1)) for i in range(60)]
    L = [tx(rng.randint(0, 200), rng.choice(amounts)) for _ in range(3000)]
    B = [tx(rng.randint(0, 200), rng.choice(amounts)) for _ in range(3000)]
    t = time.perf_counter()
    res = reconcile(L, B)
    elapsed = time.perf_counter() - t
    n, _ = check(res, L, B)
    assert n > 0
    assert elapsed < 8.0, elapsed
