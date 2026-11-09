Add monthly budgets with rollover, in a new module `ledger/budget.py`.

```python
budget_report(ledger, budgets, start_month, end_month, rollover_cap=None) -> dict
```

- `budgets`: `{category: Money}`, the monthly budget for each category. Categories that aren't in `budgets`
  are ignored entirely.
- `start_month`, `end_month`: strings `"YYYY-MM"`, inclusive. Raise `ValueError` if either is malformed
  (it must be exactly 4 digits, `-`, 2 digits, with a month from 01 to 12) or if `start_month > end_month`.
- `rollover_cap`: `None` (no cap) or a `Money`; the most that can carry into the next month.

Return `{month: {category: row}}` with an entry for **every** month in the range (including months with no
transactions), in month order, and for every budgeted category in each month. Each `row` is a dict with
these `Money` values:

- `budget`: the category's monthly budget
- `carried_in`: what carried over from the previous month (zero in `start_month`)
- `spent`: net spending in that category that month: minus the sum of all its transaction amounts that month
  (expenses are negative amounts, so they increase `spent`; refunds are positive amounts and reduce it). If the
  refunds outweigh the expenses, `spent` is negative.
- `available`: `budget + carried_in`
- `remaining`: `available - spent` (negative when overspent)

What carries into the next month is `remaining`, but never below zero (overspending is not carried forward
as debt), and never above `rollover_cap` when a cap is given. Transactions outside the month range don't
affect anything, including carry-over.

All amounts use the category's budget currency. If a budgeted category has a transaction in a different
currency inside the range, raise `ValueError`.

Keep the existing behaviour and tests working.
