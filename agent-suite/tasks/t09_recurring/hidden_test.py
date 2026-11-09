from datetime import date as D
import time
import pytest
from ledger import Money, Ledger
from ledger.recurring import Recurrence, occurrences, expand


def R(start, freq, **kw):
    return Recurrence("rent", Money("-1000"), "housing", start, freq, **kw)


def test_monthly_month_end_anchor():
    r = R(D(2026, 1, 31), "monthly")
    assert occurrences(r, D(2026, 1, 1), D(2026, 6, 30)) == [
        D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30), D(2026, 5, 31), D(2026, 6, 30)]


def test_monthly_leap_year_and_interval():
    r = R(D(2027, 12, 30), "monthly", interval=2)
    assert occurrences(r, D(2027, 1, 1), D(2028, 8, 31)) == [
        D(2027, 12, 30), D(2028, 2, 29), D(2028, 4, 30), D(2028, 6, 30), D(2028, 8, 30)]


def test_yearly_feb29():
    r = R(D(2024, 2, 29), "yearly")
    assert occurrences(r, D(2024, 1, 1), D(2028, 12, 31)) == [
        D(2024, 2, 29), D(2025, 2, 28), D(2026, 2, 28), D(2027, 2, 28), D(2028, 2, 29)]


def test_weekly_count_with_skip_uses_up_count():
    r = R(D(2026, 3, 2), "weekly", count=4, skip=(D(2026, 3, 9),))
    assert occurrences(r, D(2026, 1, 1), D(2026, 12, 31)) == [D(2026, 3, 2), D(2026, 3, 16), D(2026, 3, 23)]


def test_until_inclusive_and_count_whichever_first():
    r = R(D(2026, 1, 15), "monthly", until=D(2026, 4, 15))
    assert occurrences(r, D(2026, 1, 1), D(2026, 12, 31))[-1] == D(2026, 4, 15)
    r2 = R(D(2026, 1, 15), "monthly", until=D(2026, 12, 31), count=2)
    assert occurrences(r2, D(2026, 1, 1), D(2026, 12, 31)) == [D(2026, 1, 15), D(2026, 2, 15)]
    r3 = R(D(2026, 1, 15), "monthly", until=D(2026, 2, 20), count=10)
    assert occurrences(r3, D(2026, 1, 1), D(2026, 12, 31)) == [D(2026, 1, 15), D(2026, 2, 15)]


def test_window_starts_after_rule():
    r = R(D(2020, 1, 31), "monthly")
    assert occurrences(r, D(2026, 2, 1), D(2026, 3, 31)) == [D(2026, 2, 28), D(2026, 3, 31)]


def test_count_zero_and_window_before_start():
    assert occurrences(R(D(2026, 1, 1), "weekly", count=0), D(2026, 1, 1), D(2026, 12, 31)) == []
    assert occurrences(R(D(2026, 6, 1), "weekly"), D(2026, 1, 1), D(2026, 5, 31)) == []


def test_unbounded_rule_is_fast():
    r = R(D(1900, 1, 1), "weekly")
    t = time.perf_counter()
    got = occurrences(r, D(2026, 1, 1), D(2026, 1, 31))
    assert len(got) in (4, 5)
    assert time.perf_counter() - t < 1.0


def test_validation():
    with pytest.raises(ValueError):
        occurrences(R(D(2026, 1, 1), "daily"), D(2026, 1, 1), D(2026, 2, 1))
    with pytest.raises(ValueError):
        occurrences(R(D(2026, 1, 1), "weekly", interval=0), D(2026, 1, 1), D(2026, 2, 1))
    with pytest.raises(ValueError):
        occurrences(R(D(2026, 1, 1), "weekly", count=-1), D(2026, 1, 1), D(2026, 2, 1))


def test_expand_and_add_recurring():
    r = R(D(2026, 1, 31), "monthly", count=3)
    txs = expand(r, D(2026, 1, 1), D(2026, 12, 31))
    assert [t.date for t in txs] == [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31)]
    assert all(t.tags == ("recurring",) and t.amount == Money("-1000") and t.category == "housing"
               and t.description == "rent" for t in txs)
    L = Ledger()
    assert L.add_recurring(r, D(2026, 2, 1), D(2026, 12, 31)) == 2
    assert len(L.transactions) == 2 and L.balance() == Money("-2000")
