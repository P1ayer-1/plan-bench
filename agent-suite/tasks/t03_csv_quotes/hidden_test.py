import pytest
from ledger import Money
from ledger.parser import parse_csv

H = "date,description,amount,category,tags\n"

def test_quoted_comma():
    [t] = parse_csv(H + '2026-03-02,"Dinner, with friends",-58.20,food,social\n')
    assert t.description == "Dinner, with friends" and t.amount == Money("-58.20") and t.tags == ("social",)

def test_escaped_quote():
    [t] = parse_csv(H + '2026-03-02,"The ""Best"" Cafe",-3.00,food,\n')
    assert t.description == 'The "Best" Cafe'

def test_crlf():
    txs = parse_csv((H + "2026-01-01,A,-1.00,x,\n2026-01-02,B,-2.00,y,t\n").replace("\n", "\r\n"))
    assert [t.description for t in txs] == ["A","B"] and txs[1].tags == ("t",)

def test_missing_tags_column():
    [t] = parse_csv(H + "2026-01-01,A,-1.00,x\n")
    assert t.tags == ()

def test_bad_row_line_number():
    with pytest.raises(ValueError, match="3"):
        parse_csv(H + "2026-01-01,A,-1.00,x,\n2026-01-02,B\n")

def test_plain_still_works():
    txs = parse_csv(H + "2026-01-01,A,-1.00,x,a;b\n")
    assert txs[0].tags == ("a","b")
