from datetime import date
from ledger import Money, Ledger, Transaction
from ledger.report import monthly_summary, largest_expenses

def tx(d, amt, cat="c", desc=None): return Transaction(date.fromisoformat(d), desc or d, Money(amt), cat)

def test_summary_groups_by_month_and_sums():
    l = Ledger([tx("2026-03-05","-10","food"), tx("2026-01-20","-1","food"), tx("2026-01-21","-2","food"),
                tx("2026-01-22","5","inc")])
    s = monthly_summary(l)
    assert list(s) == ["2026-01","2026-03"]
    assert s["2026-01"] == {"food": Money("-3"), "inc": Money("5")}
    assert s["2026-03"] == {"food": Money("-10")}

def test_summary_days_do_not_split_months():
    s = monthly_summary(Ledger([tx("2026-01-01","1"), tx("2026-01-31","1")]))
    assert s == {"2026-01": {"c": Money("2")}}

def test_largest_expenses_order_and_n():
    l = Ledger([tx("2026-01-01","-5",desc="a"), tx("2026-01-02","-50",desc="b"), tx("2026-01-03","0",desc="z"),
                tx("2026-01-04","-20",desc="c"), tx("2026-01-05","100",desc="d"), tx("2026-01-06","-1",desc="e")])
    assert [t.description for t in largest_expenses(l)] == ["b","c","a"]
    assert [t.description for t in largest_expenses(l, n=1)] == ["b"]
    assert [t.description for t in largest_expenses(l, n=10)] == ["b","c","a","e"]
