Add recurring transactions to the ledger library, in a new module `ledger/recurring.py`.

## `Recurrence`

A frozen dataclass with fields, in this order:

- `description: str`
- `amount: Money`
- `category: str`
- `start: date`: the first occurrence
- `freq: str`: one of `"weekly"`, `"monthly"`, `"yearly"`
- `interval: int = 1`: every `interval` weeks / months / years
- `count: int | None = None`: total number of occurrences, counted from `start`
- `until: date | None = None`: last allowed date (inclusive)
- `skip: tuple = ()`: dates on which the occurrence is cancelled

## `occurrences(rule, window_start, window_end) -> list[date]`

Occurrence number k (k = 0, 1, 2, ...) falls on:

- weekly: `start + 7 * interval * k` days
- monthly: the same day of the month as `start`, `interval * k` months after `start`'s month. If that month is
  too short, use its last day. Always aim for `start`'s day: a rule starting Jan 31 falls on Feb 28 (or 29),
  then Mar 31, then Apr 30, not on the 28th forever.
- yearly: `start`'s month and day, `interval * k` years later. A Feb 29 start falls on Feb 28 in non-leap years.

Limits:

- With `count`, only occurrences k < count exist. Skipped occurrences still use up the count.
- With `until`, only occurrences on or before `until` exist. If both are given, whichever ends first wins.
  With neither, the rule never ends.
- Occurrences whose date is in `skip` are dropped.

Return the remaining occurrence dates that fall within `[window_start, window_end]` (inclusive), in ascending order.
It must stay fast for a rule that never ends (only walk as far as the window needs).

Raise `ValueError` if `freq` is not one of the three values, if `interval < 1`, or if `count` is negative.

## `expand(rule, window_start, window_end) -> list[Transaction]`

One `Transaction` per date from `occurrences`, using the rule's description, amount and category, with
`tags=("recurring",)`.

## `Ledger.add_recurring(rule, window_start, window_end) -> int`

Append the expanded transactions to the ledger and return how many were added.

Keep the existing behaviour and tests working.
