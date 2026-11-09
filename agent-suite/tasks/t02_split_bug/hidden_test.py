import pytest
from decimal import Decimal
from ledger import Money

def amounts(parts): return [str(p.amount) for p in parts]

def test_example():
    assert amounts(Money("10.00").split(3)) == ["3.34","3.33","3.33"]

def test_negative():
    assert amounts(Money("-10.00").split(3)) == ["-3.34","-3.33","-3.33"]

@pytest.mark.parametrize("amt,n", [("0.05",3),("100.00",7),("1.00",1),("0.00",4),("-0.07",2),("999.99",13)])
def test_sums_and_spread(amt, n):
    parts = Money(amt).split(n)
    assert len(parts) == n
    assert sum((p.amount for p in parts), Decimal("0")) == Decimal(amt)
    assert max(p.amount for p in parts) - min(p.amount for p in parts) <= Decimal("0.01")

def test_currency_kept():
    assert all(p.currency == "EUR" for p in Money("1", "EUR").split(3))

@pytest.mark.parametrize("n", [0, -2])
def test_bad_n(n):
    with pytest.raises(ValueError):
        Money("1").split(n)
