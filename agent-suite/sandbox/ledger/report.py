from .money import Money


def monthly_summary(ledger):
    """Return {"YYYY-MM": {category: Money}} with categories summed per month."""
    result = {}
    for tx in ledger.transactions:
        m = f"{tx.date.year:04d}-{tx.date.month:02d}"
        if m not in result:
            result[m] = {}
        if tx.category not in result[m]:
            result[m][tx.category] = Money.zero(tx.amount.currency)
        result[m][tx.category] = result[m][tx.category] + tx.amount
    return dict(sorted(result.items()))


def largest_expenses(ledger, n=3):
    """Return the n most negative transactions, most negative first."""
    expenses = [tx for tx in ledger.transactions if tx.amount.amount < 0]
    return sorted(expenses, key=lambda tx: tx.amount.amount)[:n]
