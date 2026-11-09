import argparse, sys
from datetime import date
from .ledger import Ledger
from .money import Money
from .parser import parse_csv
from .report import monthly_summary


def _date(s):
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid date: {s}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ledger")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summary"); s.add_argument("file")
    b = sub.add_parser("balance"); b.add_argument("file")
    b.add_argument("--since", type=_date); b.add_argument("--until", type=_date); b.add_argument("--category")
    args = ap.parse_args(argv)
    with open(args.file) as f:
        ledger = Ledger(parse_csv(f.read()))
    if args.cmd == "summary":
        for month, cats in monthly_summary(ledger).items():
            print(month)
            for cat, total in sorted(cats.items()):
                print(f"  {cat}: {total}")
    else:
        total = Money.zero()
        for tx in ledger.query(category=args.category, start=args.since, end=args.until):
            total = total + tx.amount
        print(f"Balance: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
