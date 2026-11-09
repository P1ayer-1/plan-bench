Bug report: `Money("10.00").split(3)` returns three parts of 3.33, which only add up to 9.99. A cent disappears.

Fix `Money.split(n)` so that:
- the parts always sum exactly to the original amount,
- parts differ from each other by at most one cent,
- any extra cents go to the earliest parts (e.g. 10.00 split 3 -> 3.34, 3.33, 3.33),
- it works for negative amounts too (e.g. -10.00 split 3 -> -3.34, -3.33, -3.33),
- `split(0)` or a negative n raises `ValueError`.
