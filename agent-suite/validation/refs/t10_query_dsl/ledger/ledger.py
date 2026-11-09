from dataclasses import dataclass, field
from datetime import date
from .money import Money


@dataclass(frozen=True)
class Transaction:
    date: date
    description: str
    amount: Money
    category: str
    tags: tuple = field(default_factory=tuple)


class Ledger:
    def __init__(self, transactions=None):
        self.transactions = list(transactions or [])

    def add(self, tx):
        self.transactions.append(tx)

    def query(self, category=None, start=None, end=None):
        """Return transactions matching all given filters (dates inclusive)."""
        out = []
        for tx in self.transactions:
            if category is not None and tx.category != category:
                continue
            if start is not None and tx.date < start:
                continue
            if end is not None and tx.date > end:
                continue
            out.append(tx)
        return out

    def balance(self):
        total = Money.zero()
        for tx in self.transactions:
            total = total + tx.amount
        return total

    def dedupe(self):
        """Remove duplicate transactions (same date, description and amount),
        keeping the first occurrence and preserving order."""
        result = []
        for tx in self.transactions:
            key = (tx.date, tx.description, tx.amount)
            if key not in [(t.date, t.description, t.amount) for t in result]:
                result.append(tx)
        self.transactions = result
        return self

    def search(self, query):
        from .query import compile_query
        match = compile_query(query)
        return [tx for tx in self.transactions if match(tx)]
