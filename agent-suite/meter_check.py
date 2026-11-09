#!/usr/bin/env python3
"""Check the Command Code credit estimate against Command Code's own per-request costs.

Pairs each record from fetch_cc_usage.py with the proxy-log request that has the same input and output
token counts and the closest timestamp (within --max-skew-s), then compares Command Code's `total_cost`
with costs.billed() for that request (tokens x plan rate, x2 in peak hours).

  python meter_check.py --config suite_config.json --usage results/commandcode_usage.jsonl
"""
import argparse, json
from collections import defaultdict
from pathlib import Path

from config import load_config
from costs import billed, is_peak, parse_ts, price_tokens

ROOT = Path(__file__).parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="suite_config.json")
    ap.add_argument("--usage", default="results/commandcode_usage.jsonl")
    ap.add_argument("--max-skew-s", type=float, default=60)
    a = ap.parse_args()
    cfg = load_config(a.config)
    sides = {s["name"]: s for s in cfg["sides"] if (s.get("billing") or {}).get("basis") == "credits"}
    usage = [json.loads(l) for l in open(ROOT / a.usage, encoding="utf-8") if l.strip()]
    proxy = [json.loads(l) for l in open(ROOT / cfg["proxy_log"], encoding="utf-8") if l.strip()]
    candidates = defaultdict(list)
    for p in proxy:
        if p.get("side") in sides and p.get("status") == 200 and p.get("prompt_tokens") is not None:
            candidates[(p["prompt_tokens"], p.get("completion_tokens") or 0)].append(p)

    used, rows = set(), []
    for u in usage:
        t = parse_ts(u["ts"])
        best = None
        for p in candidates.get((u["tokens_in"], u["tokens_out"]), []):
            if id(p) in used:
                continue
            skew = abs((parse_ts(p["ts"]) - t).total_seconds())
            if skew <= a.max_skew_s and (best is None or skew < best[0]):
                best = (skew, p)
        if not best:
            rows.append({"ts": u["ts"], "matched": False, "actual": u["total_cost"]})
            continue
        p = best[1]
        used.add(id(p))
        side = sides[p["side"]]
        rate = (side.get("billing") or {}).get("rate") or side["list_price"]
        rows.append({"ts": u["ts"], "matched": True, "side": p["side"], "peak": is_peak(p["ts"], side["billing"].get("peak")),
                     "actual": u["total_cost"], "estimate": billed(p, side), "base_rate": price_tokens(p, rate),
                     "skew_s": round(best[0], 1)})

    m = [r for r in rows if r["matched"]]
    print(f"Command Code records: {len(rows)}; matched to proxy log: {len(m)}; unmatched: {len(rows) - len(m)}")
    for label, sel in (("all matched", m), ("peak", [r for r in m if r["peak"]]), ("off-peak", [r for r in m if not r["peak"]])):
        if not sel:
            continue
        act, est, base = sum(r["actual"] for r in sel), sum(r["estimate"] for r in sel), sum(r["base_rate"] for r in sel)
        exact = sum(abs(r["actual"] - r["estimate"]) <= max(1e-9, 1e-3 * r["actual"]) for r in sel)
        print(f"  {label:12} n={len(sel):4}  actual ${act:.6f}  our estimate ${est:.6f}  ratio {est / act:.4f}  "
              f"(off-peak-rate formula ratio {base / act:.4f})  per-request exact: {exact}/{len(sel)}")
    out = ROOT / Path(a.usage).with_name("meter_check.json")
    json.dump(rows, open(out, "w", encoding="utf-8"), indent=1)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
