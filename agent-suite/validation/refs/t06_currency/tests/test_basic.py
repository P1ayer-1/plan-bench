from datetime import date
from ledger import Money, Ledger, Transaction
from ledger.parser import parse_csv
from ledger.report import monthly_summary

CSV = """date,description,amount,category,tags
2026-01-03,Coffee,-4.50,food,morning
2026-01-15,Salary,3000.00,income,
2026-02-01,Rent,-1200.00,housing,fixed;monthly
"""


def test_money_add():
    assert Money("1.10") + Money("2.20") == Money("3.30")


def test_parse_and_balance():
    l = Ledger(parse_csv(CSV))
    assert len(l.transactions) == 3
    assert l.balance() == {"USD": Money("1795.50")}


def test_query_category():
    l = Ledger(parse_csv(CSV))
    assert [t.description for t in l.query(category="food")] == ["Coffee"]


def test_summary():
    s = monthly_summary(Ledger(parse_csv(CSV)))
    assert list(s) == ["2026-01", "2026-02"]
    assert s["2026-02"]["housing"] == Money("-1200.00")
