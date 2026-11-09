Add bank-statement reconciliation in a new module `ledger/reconcile.py`.

```python
reconcile(ledger_txs, bank_txs, max_days=3) -> Reconciliation
```

`Reconciliation` is a dataclass with three list fields: `matched` (a list of `(ledger_tx, bank_tx)` tuples),
`unmatched_ledger` and `unmatched_bank`.

Rules:

- A ledger transaction and a bank transaction **may be paired** only if their amounts are equal (same
  `Money`, currency included) and their dates are at most `max_days` days apart (either direction).
  Descriptions and categories are ignored.
- Each transaction is used in at most one pair.
- The result must contain the **largest possible number of pairs**.
- Among all pairings with that largest number of pairs, choose one with the **smallest total date
  distance** (the sum of |ledger date − bank date| in days over all pairs). If several pairings tie on
  both, any of them is acceptable.
- `matched` is ordered by the ledger transaction's position in `ledger_txs`. Both unmatched lists keep the
  input order.
- The inputs may contain identical-looking transactions (same date, amount and description); treat each
  list element as a separate transaction.
- It must handle a few thousand transactions on each side in well under a few seconds, assuming any single
  amount appears at most ~100 times per side.

Keep the existing behaviour and tests working.
