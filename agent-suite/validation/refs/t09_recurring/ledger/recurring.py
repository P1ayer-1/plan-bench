import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from .money import Money
from .ledger import Transaction


@dataclass(frozen=True)
class Recurrence:
    description: str
    amount: Money
    category: str
    start: date
    freq: str
    interval: int = 1
    count: Optional[int] = None
    until: Optional[date] = None
    skip: tuple = ()


def _clamp(year, month, day):
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _nth(rule, k):
    s = rule.start
    if rule.freq == "weekly":
        return s + timedelta(days=7 * rule.interval * k)
    if rule.freq == "monthly":
        m = s.month - 1 + rule.interval * k
        return _clamp(s.year + m // 12, m % 12 + 1, s.day)
    return _clamp(s.year + rule.interval * k, s.month, s.day)


def _first_k(rule, window_start):
    """Smallest k whose occurrence could be >= window_start (a safe lower bound)."""
    s = rule.start
    if window_start <= s:
        return 0
    if rule.freq == "weekly":
        return (window_start - s).days // (7 * rule.interval)
    if rule.freq == "monthly":
        months = (window_start.year - s.year) * 12 + window_start.month - s.month
        return max(months // rule.interval - 1, 0)
    return max((window_start.year - s.year) // rule.interval - 1, 0)


def occurrences(rule, window_start, window_end):
    if rule.freq not in ("weekly", "monthly", "yearly"):
        raise ValueError(f"unknown freq {rule.freq!r}")
    if rule.interval < 1:
        raise ValueError("interval must be >= 1")
    if rule.count is not None and rule.count < 0:
        raise ValueError("count must be >= 0")
    skip = set(rule.skip)
    out = []
    k = _first_k(rule, window_start)
    while True:
        if rule.count is not None and k >= rule.count:
            break
        d = _nth(rule, k)
        if (rule.until is not None and d > rule.until) or d > window_end:
            break
        if d >= window_start and d not in skip:
            out.append(d)
        k += 1
    return out


def expand(rule, window_start, window_end):
    return [Transaction(d, rule.description, rule.amount, rule.category, ("recurring",))
            for d in occurrences(rule, window_start, window_end)]
