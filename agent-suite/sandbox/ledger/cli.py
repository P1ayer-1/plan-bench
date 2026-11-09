import argparse, sys
from .ledger import Ledger
from .parser import parse_csv
from .report import monthly_summary


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ledger")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summary", help="monthly category summary")
    s.add_argument("file")
    args = ap.parse_args(argv)

    with open(args.file) as f:
        ledger = Ledger(parse_csv(f.read()))
    if args.cmd == "summary":
        for month, cats in monthly_summary(ledger).items():
            print(month)
            for cat, total in sorted(cats.items()):
                print(f"  {cat}: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
