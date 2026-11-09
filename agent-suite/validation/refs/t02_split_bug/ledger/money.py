from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


class Money:
    """An amount of money in a single currency, stored to the cent."""

    def __init__(self, amount, currency="USD"):
        self.amount = Decimal(str(amount)).quantize(CENT, rounding=ROUND_HALF_UP)
        self.currency = currency

    def __add__(self, other):
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other):
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor):
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __neg__(self):
        return Money(-self.amount, self.currency)

    def __eq__(self, other):
        return isinstance(other, Money) and self.amount == other.amount and self.currency == other.currency

    def __hash__(self):
        return hash((self.amount, self.currency))

    def __lt__(self, other):
        return self.amount < other.amount

    def __repr__(self):
        return f"Money('{self.amount}', '{self.currency}')"

    def __str__(self):
        return f"{self.amount} {self.currency}"

    def split(self, n):
        """Split into n parts that sum exactly to self; extra cents go first."""
        if n <= 0:
            raise ValueError("n must be positive")
        cents = int(self.amount / CENT)
        sign = -1 if cents < 0 else 1
        q, r = divmod(abs(cents), n)
        return [Money(sign * (q + (1 if i < r else 0)) * CENT, self.currency) for i in range(n)]

    @classmethod
    def zero(cls, currency="USD"):
        return cls(0, currency)
