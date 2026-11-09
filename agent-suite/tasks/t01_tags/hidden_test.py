from datetime import date
from ledger import Money, Ledger, Transaction

def tx(d, desc, amt, cat, tags=()):
    return Transaction(date.fromisoformat(d), desc, Money(amt), cat, tuple(tags))

L = Ledger([tx("2026-01-01","a","-1","food",["x","y"]), tx("2026-01-05","b","-2","food",["y"]),
            tx("2026-02-01","c","-3","fun",["x"]), tx("2026-02-02","d","-4","fun")])

def test_tag_filter():
    assert [t.description for t in L.query(tag="x")] == ["a","c"]

def test_tag_combines():
    assert [t.description for t in L.query(tag="y", start=date(2026,1,2))] == ["b"]
    assert [t.description for t in L.query(tag="x", category="fun")] == ["c"]

def test_unknown_tag():
    assert L.query(tag="nope") == []

def test_tags_list():
    assert L.tags() == ["x","y"]
    assert Ledger().tags() == []

def test_no_tag_unchanged():
    assert len(L.query()) == 4
