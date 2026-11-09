from .money import Money


def _month(tx):
    return f"{tx.date.year:04d}-{tx.date.month:02d}"


def group_by_month(transactions):
    out = {}
    for tx in transactions:
        out.setdefault(_month(tx), []).append(tx)
    return dict(sorted(out.items()))


def totals_by_category(transactions):
    out = {}
    for tx in transactions:
        out[tx.category] = out.get(tx.category, Money.zero(tx.amount.currency)) + tx.amount
    return out


def monthly_summary(ledger):
    return {m: totals_by_category(txs) for m, txs in group_by_month(ledger.transactions).items()}


def category_share(ledger, month):
    spend = [tx for tx in group_by_month(ledger.transactions).get(month, []) if tx.amount.amount < 0]
    totals = totals_by_category(spend)
    whole = sum(-t.amount for t in totals.values())
    return {c: float(-t.amount / whole) for c, t in totals.items()} if whole else {}


def largest_expenses(ledger, n=3):
    expenses = [tx for tx in ledger.transactions if tx.amount.amount < 0]
    return sorted(expenses, key=lambda tx: tx.amount.amount)[:n]
