import csv, io
from datetime import date
from .money import Money
from .ledger import Transaction

HEADER = ["date", "description", "amount", "category", "tags"]


def parse_csv(text):
    rows = list(csv.reader(io.StringIO(text.strip())))
    rows = [(i + 1, r) for i, r in enumerate(rows) if any(c.strip() for c in r)]
    if not rows:
        return []
    header = [h.strip() for h in rows[0][1]]
    if header != HEADER:
        raise ValueError(f"bad header: {header}")
    out = []
    for lineno, r in rows[1:]:
        if len(r) == 4:
            r = r + [""]
        if len(r) != 5:
            raise ValueError(f"line {lineno}: expected 5 fields, got {len(r)}")
        d, desc, amt, cat, tags = r
        out.append(Transaction(date.fromisoformat(d.strip()), desc.strip(), Money(amt.strip()),
                               cat.strip(), tuple(t.strip() for t in tags.split(";") if t.strip())))
    return out
