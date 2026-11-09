#!/usr/bin/env python3
"""Download Command Code's own per-request usage records (what Studio > Usage shows) so the
credit estimate in costs.py can be checked against what the plan actually charged.

Needs a logged-in Studio session: put the browser's Cookie header for commandcode.ai in
COOKIES=... (env var, or a .env file next to this repo; never commit it). The endpoint is the
internal one Studio uses, so it may change without notice.

  python fetch_cc_usage.py --out results/commandcode_usage.jsonl [--since 2026-11-08T00:00:00Z]

Only timestamps, token counts, costs, model and status are kept (no ids, trace ids or messages).
"""
import argparse, json, os, re, sys, time
from pathlib import Path

import requests

URL = "https://api.commandcode.ai/internal/usage"


def cookie():
    if os.environ.get("COOKIES"):
        return os.environ["COOKIES"].strip()
    for p in (Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"):
        if p.exists():
            m = re.search(r"^COOKIES\s*=\s*(.*)$", p.read_text(encoding="utf-8"), re.M)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    sys.exit("set COOKIES (Cookie header from a logged-in commandcode.ai Studio session)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--since", help="stop once records are older than this ISO time")
    a = ap.parse_args()
    s = requests.Session()
    s.headers.update({"Cookie": cookie(), "User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    out, cursor, pages = [], None, 0
    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        r = s.get(URL, params=params, timeout=60)
        r.raise_for_status()
        j = r.json()
        pages += 1
        for u in j.get("usages", []):
            m = u.get("meta") or {}
            out.append({"ts": u["createdAt"], "tokens_in": int(u["tokensIn"] or 0), "tokens_out": int(u["tokensOut"] or 0),
                        "duration_ms": int(u["durationTotal"] or 0), "status": u.get("status"), "model": m.get("model"),
                        "total_cost": m.get("totalCost"), "input_cost": m.get("inputCost"),
                        "output_cost": m.get("outputCost"), "cache_cost": m.get("cacheCost")})
        cursor = j.get("nextCursor")
        oldest = out[-1]["ts"] if out else None
        print(f"page {pages}: {len(out)} records, oldest {oldest}", flush=True)
        if not cursor or not j.get("usages") or (a.since and oldest and oldest < a.since):
            break
        time.sleep(0.3)
    if a.since:
        out = [u for u in out if u["ts"] >= a.since]
    out.sort(key=lambda u: u["ts"])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for u in out:
            f.write(json.dumps(u) + "\n")
    print(f"wrote {len(out)} records to {a.out}")


if __name__ == "__main__":
    main()
