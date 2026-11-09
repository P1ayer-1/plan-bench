from datetime import date
from ledger import Money, Ledger, Transaction
from ledger.report import monthly_summary, group_by_month, totals_by_category, category_share

def tx(d, desc, amt, cat): return Transaction(date.fromisoformat(d), desc, Money(amt), cat)
TXS = [tx("2026-02-03","r","-100","rent"), tx("2026-01-01","a","-30","food"),
       tx("2026-01-09","b","-10","food"), tx("2026-01-15","s","500","income"), tx("2026-01-20","c","-60","fun")]
L = Ledger(TXS)

def test_group_by_month():
    g = group_by_month(TXS)
    assert list(g) == ["2026-01","2026-02"]
    assert [t.description for t in g["2026-01"]] == ["a","b","s","c"]

def test_totals_by_category():
    t = totals_by_category(TXS)
    assert t["food"] == Money("-40") and t["income"] == Money("500") and t["rent"] == Money("-100")

def test_summary_unchanged():
    s = monthly_summary(L)
    assert s == {"2026-01": {"food": Money("-40"), "income": Money("500"), "fun": Money("-60")},
                 "2026-02": {"rent": Money("-100")}}

def test_category_share():
    sh = category_share(L, "2026-01")
    assert set(sh) == {"food","fun"}
    assert abs(sh["food"]-0.4) < 1e-9 and abs(sh["fun"]-0.6) < 1e-9

def test_share_empty():
    assert category_share(L, "2025-12") == {}
    assert category_share(Ledger([tx("2026-03-01","s","5","income")]), "2026-03") == {}
