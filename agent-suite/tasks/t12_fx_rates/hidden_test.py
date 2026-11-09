from datetime import date as D
from decimal import Decimal
import pytest
from ledger import Money, Ledger, Transaction
from ledger.fx import RateTable, convert


def close(a, b):
    return abs(Decimal(a) - Decimal(b)) <= abs(Decimal(b)) * Decimal("1e-24")


def table():
    t = RateTable()
    t.add(D(2026, 1, 1), "EUR", "USD", "1.10")
    t.add(D(2026, 2, 1), "EUR", "USD", "1.20")
    t.add(D(2026, 1, 1), "USD", "JPY", "150")
    t.add(D(2026, 1, 1), "GBP", "EUR", Decimal("1.15"))
    return t


def test_same_currency_and_direct():
    t = table()
    assert t.rate("CHF", "CHF", D(2020, 1, 1)) == 1
    assert t.rate("EUR", "USD", D(2026, 1, 15)) == Decimal("1.10")
    assert t.rate("EUR", "USD", D(2026, 2, 1)) == Decimal("1.20")
    assert t.rate("EUR", "USD", D(2026, 12, 31)) == Decimal("1.20")


def test_effective_dates_and_out_of_order_adds():
    t = table()
    t.add(D(2026, 1, 20), "EUR", "USD", "1.15")
    assert t.rate("EUR", "USD", D(2026, 1, 19)) == Decimal("1.10")
    assert t.rate("EUR", "USD", D(2026, 1, 25)) == Decimal("1.15")
    assert t.rate("EUR", "USD", D(2026, 2, 5)) == Decimal("1.20")
    t.add(D(2026, 2, 1), "EUR", "USD", "1.25")
    assert t.rate("EUR", "USD", D(2026, 2, 5)) == Decimal("1.25")


def test_before_first_rate_is_keyerror():
    with pytest.raises(KeyError):
        table().rate("EUR", "USD", D(2025, 12, 31))


def test_inverse_is_exact():
    t = table()
    r = t.rate("USD", "EUR", D(2026, 1, 10))
    assert close(r, Decimal(1) / Decimal("1.10"))
    assert r != Decimal("0.91") and r != Decimal("0.909")  # not rounded


def test_triangulation_via_usd():
    t = table()
    assert t.rate("EUR", "JPY", D(2026, 1, 10)) == Decimal("165")
    assert close(t.rate("JPY", "EUR", D(2026, 1, 10)), Decimal(1) / Decimal("165"))


def test_no_chaining_beyond_usd():
    # GBP->EUR exists and EUR->USD exists, but GBP has no USD leg: rule 4 must not chain further.
    with pytest.raises(KeyError):
        table().rate("GBP", "USD", D(2026, 1, 10))
    with pytest.raises(KeyError):
        table().rate("GBP", "JPY", D(2026, 1, 10))


def test_convert_rounds_once():
    t = RateTable()
    t.add(D(2026, 1, 1), "USD", "EUR", "0.333333")
    t.add(D(2026, 1, 1), "EUR", "JPY", "3.000003")
    assert convert(Money("100.00"), "EUR", t, D(2026, 1, 2)) == Money("33.33", "EUR")
    assert convert(Money("0.03", "USD"), "EUR", t, D(2026, 1, 2)) == Money("0.01", "EUR")
    # USD->JPY: no direct or inverse rate, and the via-USD route needs USD->JPY itself, which is missing
    with pytest.raises(KeyError):
        convert(Money("1"), "JPY", t, D(2026, 1, 2))


def tx(d, amt, cur):
    return Transaction(d, "x", Money(amt, cur), "c")


def test_balance_in_rounds_once_at_the_end():
    t = RateTable()
    t.add(D(2026, 1, 1), "EUR", "USD", "1.005")
    L = Ledger([tx(D(2026, 1, 5), "1.00", "EUR") for _ in range(3)])
    # each converts to 1.005; per-transaction rounding would give 3.03, summing first gives 3.015 -> 3.02
    assert L.balance_in("USD", t) == Money("3.02", "USD")


def test_balance_in_uses_each_date_or_fixed_date():
    t = table()
    L = Ledger([tx(D(2026, 1, 15), "100", "EUR"), tx(D(2026, 2, 15), "100", "EUR"), tx(D(2026, 2, 16), "-50", "USD")])
    assert L.balance_in("USD", t) == Money("180.00", "USD")
    assert L.balance_in("USD", t, on=D(2026, 1, 20)) == Money("170.00", "USD")
    assert Ledger().balance_in("JPY", t) == Money.zero("JPY")
    with pytest.raises(KeyError):
        Ledger([tx(D(2025, 6, 1), "1", "EUR")]).balance_in("USD", t)
