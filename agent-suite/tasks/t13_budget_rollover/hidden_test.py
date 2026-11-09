from datetime import date
import pytest
from ledger import Money, Ledger, Transaction
from ledger.budget import budget_report


def tx(d, amt, cat, cur="USD"):
    return Transaction(date.fromisoformat(d), "x", Money(amt, cur), cat)


L = Ledger([
    tx("2025-12-20", "-500", "food"),       # before range: ignored
    tx("2026-01-05", "-120", "food"),
    tx("2026-01-20", "-30", "food"),
    tx("2026-01-21", "15", "food"),          # refund
    tx("2026-01-03", "-50", "fun"),
    tx("2026-02-10", "-260", "food"),
    tx("2026-02-11", "-999", "rent"),       # not budgeted
    tx("2026-04-02", "-10", "food"),
    tx("2026-05-01", "-1", "food"),         # after range
])
B = {"food": Money("200"), "fun": Money("40")}


def row(r, **kw):
    return {k: Money(v) for k, v in kw.items()} == {k: r[k] for k in kw}


def test_months_and_categories():
    rep = budget_report(L, B, "2026-01", "2026-04")
    assert list(rep) == ["2026-01", "2026-02", "2026-03", "2026-04"]
    assert all(set(m) == {"food", "fun"} for m in rep.values())
    assert set(rep["2026-01"]["food"]) == {"budget", "carried_in", "spent", "available", "remaining"}


def test_rollover_no_cap():
    rep = budget_report(L, B, "2026-01", "2026-04")
    assert row(rep["2026-01"]["food"], budget="200", carried_in="0", spent="135", available="200", remaining="65")
    assert row(rep["2026-02"]["food"], carried_in="65", spent="260", available="265", remaining="5")
    assert row(rep["2026-03"]["food"], carried_in="5", spent="0", available="205", remaining="205")
    assert row(rep["2026-04"]["food"], carried_in="205", spent="10", available="405", remaining="395")


def test_overspend_does_not_carry_debt():
    rep = budget_report(L, B, "2026-01", "2026-03")
    assert row(rep["2026-01"]["fun"], spent="50", remaining="-10")
    assert row(rep["2026-02"]["fun"], carried_in="0", available="40", remaining="40")
    assert row(rep["2026-03"]["fun"], carried_in="40", available="80")


def test_cap():
    rep = budget_report(L, B, "2026-01", "2026-04", rollover_cap=Money("50"))
    assert row(rep["2026-02"]["food"], carried_in="50", available="250", remaining="-10")
    assert row(rep["2026-03"]["food"], carried_in="0", remaining="200")
    assert row(rep["2026-04"]["food"], carried_in="50", remaining="240")


def test_net_refund_month():
    L2 = Ledger([tx("2026-03-03", "80", "fun")])
    rep = budget_report(L2, {"fun": Money("40")}, "2026-03", "2026-04")
    assert row(rep["2026-03"]["fun"], spent="-80", remaining="120")
    assert row(rep["2026-04"]["fun"], carried_in="120")


def test_out_of_range_tx_do_not_affect_carry():
    rep = budget_report(L, B, "2026-02", "2026-02")
    assert row(rep["2026-02"]["food"], carried_in="0", spent="260", remaining="-60")


def test_year_boundary():
    rep = budget_report(L, B, "2025-11", "2026-01")
    assert list(rep) == ["2025-11", "2025-12", "2026-01"]
    assert row(rep["2025-12"]["food"], carried_in="200", spent="500", remaining="-100")
    assert row(rep["2026-01"]["food"], carried_in="0")


@pytest.mark.parametrize("a,b", [("2026-1", "2026-02"), ("2026-13", "2026-12"), ("2026-03", "2026-02"),
                                 ("26-01", "2026-02"), ("2026-00", "2026-01"), ("2026/01", "2026-02")])
def test_bad_months(a, b):
    with pytest.raises(ValueError):
        budget_report(L, B, a, b)


def test_currency_mismatch():
    with pytest.raises(ValueError):
        budget_report(Ledger([tx("2026-01-02", "-5", "fun", "EUR")]), B, "2026-01", "2026-01")
    # outside the range it's ignored
    budget_report(Ledger([tx("2027-01-02", "-5", "fun", "EUR")]), B, "2026-01", "2026-01")
