from .money import Money


def monthly_summary(ledger):
    months = {}
    for tx in ledger.transactions:
        months.setdefault(f"{tx.date.year:04d}-{tx.date.month:02d}", []).append(tx)
    result = {}
    for m, txs in sorted(months.items()):
        multi = len({t.amount.currency for t in txs}) > 1
        cats = {}
        for t in txs:
            k = (t.category, t.amount.currency) if multi else t.category
            cats[k] = cats.get(k, Money.zero(t.amount.currency)) + t.amount
        result[m] = cats
    return result


def largest_expenses(ledger, n=3):
    expenses = [tx for tx in ledger.transactions if tx.amount.amount < 0]
    return sorted(expenses, key=lambda tx: tx.amount.amount)[:n]
