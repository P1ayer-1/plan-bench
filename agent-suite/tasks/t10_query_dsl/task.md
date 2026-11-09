Add a search language to the ledger: `Ledger.search(query: str) -> list[Transaction]` returns the matching
transactions in their original order.

## Terms

- `category:VALUE`: category equals VALUE, case-insensitive
- `tag:VALUE`: one of the transaction's tags equals VALUE, case-insensitive
- `desc:VALUE`: VALUE appears anywhere in the description, case-insensitive
- `amount OP NUMBER`: compares the transaction amount (a `Decimal`) with NUMBER, e.g. `amount<-20`,
  `amount >= 10.50`, `amount=0`. NUMBER may be negative and may have decimals.
- `date OP YYYY-MM-DD`: compares the transaction date, e.g. `date>=2026-01-01`

OP is one of `<`, `<=`, `>`, `>=`, `=`. Whitespace around OP is allowed (`amount < -20`); no whitespace is
allowed around the `:` of the other three fields. Field names are lowercase.

VALUE is either a bare word (a run of characters other than whitespace, parentheses and `"`) or a
double-quoted string, which may contain spaces and parentheses; inside quotes, `\"` stands for a literal `"`
and `\\` for a literal backslash.

## Operators

`AND`, `OR`, `NOT` (keywords, case-insensitive) and parentheses. Precedence: `NOT` binds tightest, then
`AND`, then `OR`. Two terms or groups next to each other with no operator between them are joined by an
implicit `AND`, e.g. `category:food tag:x` = `category:food AND tag:x`.

An empty or whitespace-only query matches every transaction.

## Errors

Raise `ValueError` for any malformed query, including: an unknown field (`foo:bar`), unbalanced parentheses,
an operator with a missing operand (`category:food AND`, `OR tag:x`, `NOT`), a bad OP, an invalid number
or date, an unterminated quote, or an empty group `()`.

Example: `desc:"coffee shop" OR (category:food AND NOT tag:work) amount<-5`

Keep the existing behaviour and tests working.
