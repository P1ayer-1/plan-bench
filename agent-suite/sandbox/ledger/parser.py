from datetime import date
from .money import Money
from .ledger import Transaction

HEADER = ["date", "description", "amount", "category", "tags"]


def parse_csv(text):
    """Parse CSV text with header date,description,amount,category,tags.
    tags are separated by ';'. Returns a list of Transaction."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return []
    header = [h.strip() for h in lines[0].split(",")]
    if header != HEADER:
        raise ValueError(f"bad header: {header}")
    out = []
    for line in lines[1:]:
        d, desc, amt, cat, tags = line.split(",")
        out.append(Transaction(
            date=date.fromisoformat(d.strip()),
            description=desc.strip(),
            amount=Money(amt.strip()),
            category=cat.strip(),
            tags=tuple(t.strip() for t in tags.split(";") if t.strip()),
        ))
    return out
