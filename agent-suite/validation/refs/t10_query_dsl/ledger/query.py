"""Tiny search language: terms (field:value, amount/date comparisons), AND/OR/NOT, parentheses."""
import operator
import re
from datetime import date
from decimal import Decimal, InvalidOperation

OPS = {"<=": operator.le, ">=": operator.ge, "<": operator.lt, ">": operator.gt, "=": operator.eq}
TEXT_FIELDS = ("category", "tag", "desc")


def _read_value(q, i):
    """Read a bare word or quoted string starting at i. Returns (value, next_index)."""
    if i < len(q) and q[i] == '"':
        i += 1
        out = []
        while i < len(q):
            c = q[i]
            if c == "\\" and i + 1 < len(q) and q[i + 1] in '"\\':
                out.append(q[i + 1]); i += 2; continue
            if c == '"':
                return "".join(out), i + 1
            out.append(c); i += 1
        raise ValueError("unterminated quote")
    m = re.compile(r'[^\s()"]+').match(q, i)
    if not m:
        raise ValueError(f"missing value at {i}")
    return m.group(), m.end()


def tokenize(q):
    toks, i = [], 0
    while i < len(q):
        c = q[i]
        if c.isspace():
            i += 1
        elif c in "()":
            toks.append((c, None)); i += 1
        else:
            m = re.compile(r"(category|tag|desc):").match(q, i)
            if m:
                val, i = _read_value(q, m.end())
                toks.append(("term", (m.group(1), val)))
                continue
            m = re.compile(r"(amount|date)\s*(<=|>=|<|>|=)\s*").match(q, i)
            if m:
                field, op = m.group(1), m.group(2)
                val, i = _read_value(q, m.end())
                if field == "amount":
                    try:
                        num = Decimal(val)
                    except InvalidOperation:
                        raise ValueError(f"bad number {val!r}")
                    if not num.is_finite():
                        raise ValueError(f"bad number {val!r}")
                    toks.append(("term", (field, op, num)))
                else:
                    try:
                        toks.append(("term", (field, op, date.fromisoformat(val))))
                    except ValueError:
                        raise ValueError(f"bad date {val!r}")
                continue
            m = re.compile(r'[^\s()"]+').match(q, i)
            word = m.group() if m else q[i]
            if word.upper() in ("AND", "OR", "NOT"):
                toks.append((word.upper(), None)); i += len(word)
            else:
                raise ValueError(f"unexpected {word!r} at {i}")
    return toks


class _Parser:
    def __init__(self, toks):
        self.toks, self.i = toks, 0

    def peek(self):
        return self.toks[self.i][0] if self.i < len(self.toks) else None

    def take(self):
        t = self.toks[self.i]; self.i += 1
        return t

    def parse(self):
        node = self.or_()
        if self.peek() is not None:
            raise ValueError(f"unexpected {self.peek()!r}")
        return node

    def or_(self):
        node = self.and_()
        while self.peek() == "OR":
            self.take()
            node = ("or", node, self.and_())
        return node

    def and_(self):
        node = self.not_()
        while self.peek() in ("AND", "NOT", "term", "("):
            if self.peek() == "AND":
                self.take()
            node = ("and", node, self.not_())
        return node

    def not_(self):
        if self.peek() == "NOT":
            self.take()
            return ("not", self.not_())
        return self.atom()

    def atom(self):
        k = self.peek()
        if k == "term":
            return ("term", self.take()[1])
        if k == "(":
            self.take()
            if self.peek() == ")":
                raise ValueError("empty group")
            node = self.or_()
            if self.peek() != ")":
                raise ValueError("unbalanced parentheses")
            self.take()
            return node
        raise ValueError(f"expected a term, got {k!r}")


def compile_query(q):
    toks = tokenize(q)
    if not toks:
        return lambda tx: True
    tree = _Parser(toks).parse()

    def ev(node, tx):
        kind = node[0]
        if kind == "or":
            return ev(node[1], tx) or ev(node[2], tx)
        if kind == "and":
            return ev(node[1], tx) and ev(node[2], tx)
        if kind == "not":
            return not ev(node[1], tx)
        t = node[1]
        if t[0] == "category":
            return tx.category.lower() == t[1].lower()
        if t[0] == "tag":
            return any(tag.lower() == t[1].lower() for tag in tx.tags)
        if t[0] == "desc":
            return t[1].lower() in tx.description.lower()
        if t[0] == "amount":
            return OPS[t[1]](tx.amount.amount, t[2])
        return OPS[t[1]](tx.date, t[2])

    return lambda tx: ev(tree, tx)
