import re

from .money import Money

_MONTH = re.compile(r"^(\d{4})-(\d{2})$")


def _parse(m):
    hit = _MONTH.match(m) if isinstance(m, str) else None
    if not hit or not 1 <= int(hit.group(2)) <= 12:
        raise ValueError(f"bad month {m!r}")
    return int(hit.group(1)), int(hit.group(2))


def _months(start, end):
    y, m = _parse(start)
    ey, em = _parse(end)
    if (y, m) > (ey, em):
        raise ValueError("start_month is after end_month")
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def budget_report(ledger, budgets, start_month, end_month, rollover_cap=None):
    months = _months(start_month, end_month)
    wanted = set(months)
    net = {}  # (month, category) -> Money (sum of amounts)
    for tx in ledger.transactions:
        if tx.category not in budgets:
            continue
        m = f"{tx.date.year:04d}-{tx.date.month:02d}"
        if m not in wanted:
            continue
        cur = budgets[tx.category].currency
        if tx.amount.currency != cur:
            raise ValueError(f"{tx.category}: transaction in {tx.amount.currency}, budget in {cur}")
        key = (m, tx.category)
        net[key] = net.get(key, Money.zero(cur)) + tx.amount

    report, carry = {}, {c: Money.zero(b.currency) for c, b in budgets.items()}
    for m in months:
        report[m] = {}
        for c, budget in budgets.items():
            cur = budget.currency
            spent = -net.get((m, c), Money.zero(cur))
            available = budget + carry[c]
            remaining = available - spent
            report[m][c] = {"budget": budget, "carried_in": carry[c], "spent": spent,
                            "available": available, "remaining": remaining}
            nxt = remaining if remaining.amount > 0 else Money.zero(cur)
            if rollover_cap is not None and nxt.amount > rollover_cap.amount:
                nxt = Money(rollover_cap.amount, cur)
            carry[c] = nxt
    return report
