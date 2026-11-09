from datetime import date
import pytest
from ledger import Money, Ledger, Transaction


def tx(d, desc, amt, cat, tags=()):
    return Transaction(date.fromisoformat(d), desc, Money(amt), cat, tuple(tags))


L = Ledger([
    tx("2026-01-03", "Coffee Shop downtown", "-4.50", "food", ["work"]),          # 0
    tx("2026-01-10", "Grocer", "-62.10", "Food", []),                               # 1
    tx("2026-02-01", "Salary", "3000", "income", ["Work"]),                         # 2
    tx("2026-02-14", 'The "Fancy" Bistro (date night)', "-85", "food", ["fun"]),    # 3
    tx("2026-03-01", "Rent", "-1200", "housing", []),                               # 4
    tx("2026-03-05", "Refund", "20", "food", ["fun", "x"]),                         # 5
])


def ids(q):
    return [L.transactions.index(t) for t in L.search(q)]


def test_simple_terms():
    assert ids("category:food") == [0, 1, 3, 5]
    assert ids("tag:work") == [0, 2]
    assert ids("desc:coffee") == [0]
    assert ids("amount<-50") == [1, 3, 4]
    assert ids("amount >= 20") == [2, 5]
    assert ids("amount=-85") == [3]
    assert ids("amount = -4.5") == [0]
    assert ids("date>=2026-02-14") == [3, 4, 5]
    assert ids("date<2026-01-10") == [0]


def test_empty_query():
    assert ids("") == [0, 1, 2, 3, 4, 5]
    assert ids("   ") == [0, 1, 2, 3, 4, 5]


def test_precedence_and_implicit_and():
    assert ids("category:food AND tag:fun OR category:housing") == [3, 4, 5]
    assert ids("category:housing OR category:food AND tag:fun") == [3, 4, 5]
    assert ids("category:food tag:fun") == [3, 5]
    assert ids("(category:housing OR category:food) amount<-50") == [1, 3, 4]
    assert ids("category:housing OR category:food amount<-50") == [1, 3, 4]
    assert ids("category:food (tag:fun OR tag:work) amount<0") == [0, 3]


def test_not_binds_tightest():
    assert ids("NOT tag:fun AND category:food") == [0, 1]
    assert ids("NOT (tag:fun OR tag:work)") == [1, 4]
    assert ids("NOT NOT tag:x") == [5]
    assert ids("category:food AND NOT tag:work") == [1, 3, 5]


def test_keywords_case_insensitive():
    assert ids("category:food and not tag:work") == [1, 3, 5]
    assert ids("tag:x Or category:housing") == [4, 5]


def test_quoted_values():
    assert ids('desc:"coffee shop"') == [0]
    assert ids('desc:"(date night)"') == [3]
    assert ids('desc:"\\"Fancy\\""') == [3]
    assert ids('desc:"coffee shop" OR (category:food AND NOT tag:work) amount<-5') == [0, 1, 3]


@pytest.mark.parametrize("q", [
    "foo:bar", "(category:food", "category:food)", "category:food AND", "OR tag:x", "NOT",
    "amount<<5", "amount<abc", "date>2026-13-01", 'desc:"unterminated', "()", "amount", "category:",
])
def test_errors(q):
    with pytest.raises(ValueError):
        L.search(q)
