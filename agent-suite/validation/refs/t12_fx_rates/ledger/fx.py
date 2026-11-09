import bisect
from collections import defaultdict
from decimal import Decimal, localcontext

from .money import Money


class RateTable:
    def __init__(self):
        self._rates = defaultdict(dict)  # (base, quote) -> {date: Decimal}

    def add(self, on, base, quote, rate):
        if isinstance(rate, float):
            raise TypeError("pass rates as str, int or Decimal, not float")
        self._rates[(base, quote)][on] = Decimal(rate) if not isinstance(rate, Decimal) else rate

    def _latest(self, base, quote, on):
        series = self._rates.get((base, quote))
        if not series:
            return None
        dates = sorted(series)
        i = bisect.bisect_right(dates, on)
        return series[dates[i - 1]] if i else None

    def _simple(self, base, quote, on):
        if base == quote:
            return Decimal(1)
        r = self._latest(base, quote, on)
        if r is not None:
            return r
        r = self._latest(quote, base, on)
        if r is not None:
            with localcontext() as ctx:
                ctx.prec = 40
                return Decimal(1) / r
        return None

    def rate(self, base, quote, on):
        r = self._simple(base, quote, on)
        if r is not None:
            return r
        a, b = self._simple(base, "USD", on), self._simple("USD", quote, on)
        if a is None or b is None:
            raise KeyError(f"no rate {base}->{quote} on {on}")
        with localcontext() as ctx:
            ctx.prec = 40
            return a * b


def _exact(money, to, table, on):
    with localcontext() as ctx:
        ctx.prec = 40
        return money.amount * table.rate(money.currency, to, on)


def convert(money, to, table, on):
    return Money(_exact(money, to, table, on), to)
