Add tag support to `Ledger`:

1. `Ledger.query()` gets a new optional `tag` argument. When given, only transactions whose `tags` contain that tag are returned. It combines with the existing filters (all filters must match).
2. Add `Ledger.tags()` which returns a sorted list of every distinct tag used in the ledger.

Keep the existing tests passing.
