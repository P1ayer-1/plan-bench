"""Bank reconciliation: maximum matching on (amount, date window), then minimum total date distance."""
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Reconciliation:
    matched: list = field(default_factory=list)
    unmatched_ledger: list = field(default_factory=list)
    unmatched_bank: list = field(default_factory=list)


def _hungarian(cost):
    """Min-cost assignment for an n x m matrix with n <= m. Returns assign[row] = col."""
    n, m = len(cost), len(cost[0])
    INF = float("inf")
    u, v = [0] * (n + 1), [0] * (m + 1)
    p, way = [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [INF] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], INF, 0
            row = cost[i0 - 1]
            for j in range(1, m + 1):
                if not used[j]:
                    cur = row[j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    assign = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            assign[p[j] - 1] = j - 1
    return assign


def _match_group(ls, bs, max_days):
    """ls, bs: lists of (index, tx) with the same amount. Returns list of (li, bi)."""
    if not ls or not bs:
        return []
    flip = len(ls) > len(bs)
    rows, cols = (bs, ls) if flip else (ls, bs)
    big = (max_days + 1) * (len(rows) + 1)  # one ineligible pair costs more than any total distance
    cost = []
    for _, r in rows:
        line = []
        for _, c in cols:
            d = abs((r.date - c.date).days)
            line.append(d if d <= max_days else big)
        cost.append(line)
    out = []
    for ri, ci in enumerate(_hungarian(cost)):
        if cost[ri][ci] < big:
            a, b = rows[ri][0], cols[ci][0]
            out.append((b, a) if flip else (a, b))
    return out


def reconcile(ledger_txs, bank_txs, max_days=3):
    by_amount_l, by_amount_b = defaultdict(list), defaultdict(list)
    for i, t in enumerate(ledger_txs):
        by_amount_l[t.amount].append((i, t))
    for j, t in enumerate(bank_txs):
        by_amount_b[t.amount].append((j, t))
    pairs = []
    for amt, ls in by_amount_l.items():
        pairs += _match_group(ls, by_amount_b.get(amt, []), max_days)
    pairs.sort()
    used_l = {i for i, _ in pairs}
    used_b = {j for _, j in pairs}
    return Reconciliation(
        matched=[(ledger_txs[i], bank_txs[j]) for i, j in pairs],
        unmatched_ledger=[t for i, t in enumerate(ledger_txs) if i not in used_l],
        unmatched_bank=[t for j, t in enumerate(bank_txs) if j not in used_b],
    )
