import pytest
from datetime import date
from ledger import Money, Ledger, Transaction, CurrencyMismatch
from ledger.report import monthly_summary

def tx(d, amt, cur, cat="x"): return Transaction(date.fromisoformat(d), "t", Money(amt, cur), cat)

def test_mismatch_add_sub_lt():
    with pytest.raises(CurrencyMismatch): Money(1,"USD") + Money(1,"EUR")
    with pytest.raises(CurrencyMismatch): Money(1,"USD") - Money(1,"EUR")
    with pytest.raises(CurrencyMismatch): Money(1,"USD") < Money(1,"EUR")
    assert issubclass(CurrencyMismatch, ValueError)

def test_same_currency_ok():
    assert Money(1,"EUR") + Money(2,"EUR") == Money(3,"EUR")

def test_balance_dict():
    l = Ledger([tx("2026-01-01","10","USD"), tx("2026-01-02","5","EUR"), tx("2026-01-03","-2","USD")])
    assert l.balance() == {"USD": Money("8","USD"), "EUR": Money("5","EUR")}
    assert Ledger().balance() == {}

def test_summary_mixed():
    l = Ledger([tx("2026-01-01","10","USD","a"), tx("2026-01-02","5","EUR","a"), tx("2026-02-01","3","USD","b")])
    s = monthly_summary(l)
    assert s["2026-01"] == {("a","USD"): Money("10","USD"), ("a","EUR"): Money("5","EUR")}
    assert s["2026-02"] == {"b": Money("3","USD")}
