#!/usr/bin/env python3
"""Join run results with the proxy log; write summary.json, per_task.csv and report.md.

  python analyze.py --config suite_config.json [--meter commandcode-goat=23.40]

--meter records what a side's own dashboard says was used during the run (e.g. Command Code
Studio > Usage, before/after difference), so the report can check our credit estimate against it.
"""
import argparse, csv, json, math, random, statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from config import load_config
from costs import billed, counts, is_peak, list_value, windows

ROOT = Path(__file__).parent


def load_jsonl(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def wilson(k, n, z=1.96):
    if not n:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(c - h, 3), round(c + h, 3)


def med(xs):
    return round(statistics.median(xs), 3) if xs else None


def pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(int(q * len(xs)), len(xs) - 1)], 3)


def r4(x):
    return round(x, 4) if x is not None else None


def boot_ci(xs, n=4000, seed=12345):
    """95% percentile bootstrap CI of the mean."""
    if len(xs) < 2:
        return [None, None]
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(xs) for _ in xs) / len(xs) for _ in range(n))
    return [round(means[int(0.025 * n)], 5), round(means[int(0.975 * n) - 1], 5)]


def side_metrics(side, results, by_run, final):
    name = side["name"]
    plan = side.get("plan") or {}
    basis = (side.get("billing") or {}).get("basis", "list_value")
    rows = [r for k, r in final.items() if k[0] == name]
    runs = [r for r in results if r["side"] == name]
    reqs = [p for r in runs for p in by_run[r["run_id"]]]
    used = [p for p in reqs if counts(p)]
    pt = sum(p.get("prompt_tokens") or 0 for p in used)
    cached = sum(p.get("cached_tokens") or 0 for p in used)
    out_t = sum(p.get("completion_tokens") or 0 for p in used)
    reas = sum(p.get("reasoning_tokens") or 0 for p in used)
    lv = sum(list_value(p, side) for p in used)
    bill = sum(billed(p, side) for p in used)
    passed = sum(bool(r["passed"]) for r in rows)
    tc = sum(p.get("tool_calls") or 0 for p in used)
    bad = sum(p.get("malformed_tool_calls") or 0 for p in used)
    ttfts = [p["ttft_s"] for p in used if p.get("ttft_s") is not None]
    tps = [p["completion_tokens"] / max(p["latency_s"] - p["ttft_s"], 1e-3) for p in used
           if p.get("completion_tokens") and p.get("ttft_s") is not None and p.get("latency_s")
           and p["completion_tokens"] >= 50 and p["latency_s"] > p["ttft_s"]]
    lo, hi = wilson(passed, len(rows))
    per_run = [sum(billed(p, side) for p in by_run[r["run_id"]] if counts(p)) for r in rows]
    m = {
        "label": side.get("label", name), "model": side["model"],
        "served_models": sorted({str(p.get("served_model")) for p in used}),
        "providers": sorted({str(p.get("provider")) for p in used}),
        "first_request": min((p["ts"] for p in reqs), default=None),
        "last_request": max((p["ts"] for p in reqs), default=None),
        "runs_total": len(runs), "graded_runs": len(rows), "passed": passed,
        "pass_rate": round(passed / len(rows), 3) if rows else None, "pass_rate_95ci": [lo, hi],
        "visible_tests_passed": sum(bool(r.get("visible_passed")) for r in rows),
        "agent_timeouts": sum(bool(r["agent_timeout"]) for r in rows),
        "runs_cut_off_by_cap": sum(bool(r["capped"]) for r in runs),
        "requests": len(reqs), "billable_requests": len(used),
        "cap_responses": sum(bool(p.get("cap")) for p in reqs),
        "rate_limited_responses": sum(bool(p.get("rate_limited")) for p in reqs),
        "other_errors": sum(1 for p in reqs if p.get("error_kind") == "error" or p.get("status") == -1),
        "prompt_tokens": pt, "cached_tokens": cached, "output_tokens": out_t, "reasoning_tokens": reas,
        "cache_hit_rate": round(cached / pt, 3) if pt else None,
        "mean_requests_per_run": round(len(reqs) / len(runs), 1) if runs else None,
        "mean_prompt_tokens_per_run": round(pt / len(runs)) if runs else None,
        "list_value_usd": r4(lv),
        "billing_basis": basis, "billed_usd": r4(bill),
        "billed_missing_reported_cost": sum(1 for p in used if basis == "reported_cost" and p.get("reported_cost") is None),
        "peak_request_share": round(sum(is_peak(p["ts"], (side.get("billing") or {}).get("peak")) for p in used) / len(used), 3) if used else None,
        "billed_per_passed_task_usd": r4(bill / passed) if passed else None,
        "billed_per_graded_run_usd": r4(statistics.mean(per_run)) if per_run else None,
        "billed_per_graded_run_95ci": boot_ci(per_run),
        "list_value_per_passed_task_usd": r4(lv / passed) if passed else None,
        "tool_calls": tc, "malformed_tool_calls": bad, "malformed_tool_call_rate": round(bad / tc, 4) if tc else None,
        "median_ttft_s": med(ttfts), "p90_ttft_s": pct(ttfts, 0.9),
        "median_headers_s": med([p["headers_s"] for p in used if p.get("headers_s") is not None]),
        "median_request_latency_s": med([p["latency_s"] for p in used if p.get("latency_s") is not None]),
        "median_output_tok_per_s": med(tps),
        "median_wall_s_per_run": med([r["wall_s"] for r in rows]),
    }
    # What $10 of this product buys, in passed tasks
    if plan.get("kind") == "payg" and bill and passed:
        m["passed_tasks_per_10usd"] = round(passed / bill * 10, 1)
        m["value_multiple_vs_list"] = round(lv / bill, 2)  # list-price value delivered per $ billed
    if plan.get("kind") == "subscription":
        mc, price = plan.get("monthly_credits_usd"), plan.get("price_usd")
        m["share_of_monthly_credits_used"] = round(bill / mc, 4) if mc else None
        if passed and bill:
            per = bill / passed
            m["projected_passed_tasks_per_month"] = round(mc / per, 1)
            m["passed_tasks_per_10usd"] = round(mc / per * 10 / price, 1)
            m["plan_dollars_per_passed_task"] = r4(price * per / mc)
            m["value_multiple_vs_list"] = round(mc * (lv / bill) / price, 2)
        if plan.get("weekly_usd"):
            m["min_weeks_to_use_monthly_credits"] = round(mc / plan["weekly_usd"], 2)
        recs = [p for r in runs for p in by_run[r["run_id"]]]
        m["windows_5h"] = windows(recs, side, 5)
        m["windows_7d"] = windows(recs, side, 24 * 7)
        caps = [w for w in m["windows_5h"] if w["capped_at"]]
        m["credits_used_in_5h_windows_that_capped"] = [w["billed"] for w in caps]
    return m


def table(rows, headers):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def fmt_usd(x):
    return None if x is None else f"${x:,.4f}" if x < 1 else f"${x:,.2f}"


def report(cfg, sides, per_task, paired, meters, preflight):
    names = list(sides)
    S = lambda k: [sides[n].get(k) for n in names]
    L = []
    L.append(f"# Agent-suite results\n\n_Generated {datetime.now():%Y-%m-%d %H:%M} from `{cfg['results_dir']}/`._\n")
    L.append("## Setup\n")
    rows = []
    for n in names:
        s = next(x for x in cfg["sides"] if x["name"] == n)
        m = sides[n]
        rows.append([n, s["model"], ", ".join(m["served_models"]), ", ".join(m["providers"]),
                     m["first_request"] and m["first_request"][:16], m["last_request"] and m["last_request"][:16]])
    L.append(table(rows, ["side", "requested model", "served model(s)", "provider(s)", "first request (UTC)", "last request (UTC)"]))
    L.append(f"\nHarness: `{' '.join(cfg['agent']['cmd'][:2])}` with the same config on every side; "
             f"agent timeout {cfg['agent_timeout_s']}s; tasks: {len({t['task'] for t in per_task})}.\n")
    if preflight:
        L.append(f"Preflight: `{preflight}`\n")

    L.append("## Headline\n")
    hl = [("passed tasks per $10", "passed_tasks_per_10usd"),
          ("pass rate", "pass_rate"), ("pass rate 95% CI", "pass_rate_95ci"),
          ("graded runs", "graded_runs"),
          ("billed (own basis)", "billed_usd"), ("billing basis", "billing_basis"),
          ("list-price value delivered", "list_value_usd"),
          ("$10 buys this much list-price value (×)", "value_multiple_vs_list"),
          ("billed per passed task", "billed_per_passed_task_usd"),
          ("billed per graded run (mean)", "billed_per_graded_run_usd"),
          ("billed per graded run 95% CI", "billed_per_graded_run_95ci"),
          ("plan $ per passed task", "plan_dollars_per_passed_task"),
          ("projected passed tasks / month", "projected_passed_tasks_per_month"),
          ("min weeks to use monthly credits", "min_weeks_to_use_monthly_credits")]
    L.append(table([[lbl] + S(k) for lbl, k in hl], ["metric"] + names))
    L.append("\n_Pay-as-you-go: \"per $10\" is what this run actually spent. Subscription: \"per $10\" assumes the "
             "month's full credit allowance gets used at the credits-per-passed-task rate measured here; it "
             "can't be used faster than the weekly cap allows. \"Billed\" is in each side's own currency: "
             "provider-reported dollars, or plan credits (tokens × the plan's per-model rate, doubled in peak hours)._")

    L.append("\n## Tokens and caching\n")
    tk = ["requests", "mean_requests_per_run", "prompt_tokens", "cached_tokens", "cache_hit_rate", "output_tokens",
          "reasoning_tokens", "mean_prompt_tokens_per_run", "peak_request_share"]
    L.append(table([[k] + S(k) for k in tk], ["metric"] + names))

    L.append("\n## Speed\n")
    sp = ["median_ttft_s", "p90_ttft_s", "median_headers_s", "median_request_latency_s", "median_output_tok_per_s", "median_wall_s_per_run"]
    L.append(table([[k] + S(k) for k in sp], ["metric"] + names))

    L.append("\n## Reliability\n")
    rl = ["tool_calls", "malformed_tool_calls", "malformed_tool_call_rate", "agent_timeouts", "runs_cut_off_by_cap",
          "cap_responses", "rate_limited_responses", "other_errors", "billed_missing_reported_cost"]
    L.append(table([[k] + S(k) for k in rl], ["metric"] + names))

    for n in names:
        m = sides[n]
        if "windows_5h" in m:
            L.append(f"\n## Usage windows: {n}\n")
            L.append(table([[w["start"][:16], w["requests"], fmt_usd(w["billed"]), fmt_usd(w["list_value"]),
                             w["capped_at"] and w["capped_at"][:16]] for w in m["windows_5h"]],
                           ["5h window opened (UTC)", "requests", "credits used", "list value", "capped at"]))
            L.append("")
            L.append(table([[w["start"][:16], w["requests"], fmt_usd(w["billed"]), w["capped_at"] and w["capped_at"][:16]]
                            for w in m["windows_7d"]], ["7-day window opened (UTC)", "requests", "credits used", "capped at"]))
    if meters:
        L.append("\n## Dashboard meter check\n")
        L.append(table([[n, fmt_usd(v), fmt_usd(sides[n]["billed_usd"]),
                         f"{(sides[n]['billed_usd'] or 0) / v:.2f}" if v else None] for n, v in meters.items() if n in sides],
                       ["side", "dashboard says used", "our estimate", "estimate / dashboard"]))

    L.append("\n## Paired outcomes (same task, same repeat, both sides graded)\n")
    if paired:
        L.append(table([[f"{p['a']} vs {p['b']}", p["both"], p["only_a"], p["only_b"], p["neither"], p["n"], p["sign_test_p"]]
                        for p in paired], ["pair (A vs B)", "both passed", "only A", "only B", "neither", "pairs",
                                           "sign test p (discordant pairs)"]))
    groups = cfg.get("task_groups") or {}
    if groups:
        L.append("\n## Pass rate by task group\n")
        grows = []
        for g, members in groups.items():
            row = [f"{g} ({len(members)} tasks)"]
            for n in names:
                xs = [p for p in per_task if p["side"] == n and p["task"] in members]
                k, m = sum(x["passed"] for x in xs), sum(x["runs"] for x in xs)
                lo, hi = wilson(k, m)
                row.append(f"{k}/{m} = {k / m:.2f} [{lo}, {hi}]" if m else "-")
            grows.append(row)
        L.append(table(grows, ["group (pass rate, 95% CI)"] + names))
    L.append("\n## Per task\n")
    tasks = sorted({t["task"] for t in per_task})
    rows = []
    for t in tasks:
        row = [t]
        for n in names:
            x = next((p for p in per_task if p["side"] == n and p["task"] == t), None)
            row.append(f"{x['passed']}/{x['runs']} · {fmt_usd(x['billed_usd'] / x['runs'])}/run · {x['median_wall_s']}s" if x else "-")
        rows.append(row)
    L.append(table(rows, ["task"] + [f"{n} (passed · billed/run · median wall)" for n in names]))
    return "\n".join(L) + "\n"


def sign_test(k, n):
    """Two-sided exact binomial test, p=0.5."""
    if n == 0:
        return None
    tail = sum(math.comb(n, i) for i in range(0, min(k, n - k) + 1)) / 2 ** n
    return round(min(1.0, 2 * tail), 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="suite_config.json")
    ap.add_argument("--meter", action="append", default=[], help="side=dollars used per the side's own dashboard")
    a = ap.parse_args()
    cfg = load_config(a.config)
    out = ROOT / cfg["results_dir"]
    results = load_jsonl(out / "results.jsonl")
    proxy = load_jsonl(ROOT / cfg["proxy_log"])
    side_cfg = {s["name"]: s for s in cfg["sides"]}
    meters = {k: float(v) for k, v in (m.split("=", 1) for m in a.meter)}

    by_run = defaultdict(list)
    for r in proxy:
        by_run[r.get("run_id")].append(r)

    # one graded attempt per (side, task, repeat): the last one that wasn't cut off by a cap
    final = {}
    for r in sorted(results, key=lambda r: r["ts"]):
        if not r["capped"]:
            final[(r["side"], r["task"], r["repeat"])] = r

    present = [n for n in side_cfg if any(r["side"] == n for r in results)]
    sides = {n: side_metrics(side_cfg[n], results, by_run, final) for n in present}

    per_task = []
    for n in present:
        for task in sorted({k[1] for k in final if k[0] == n}):
            tr = [r for k, r in final.items() if k[0] == n and k[1] == task]
            treq = [p for r in tr for p in by_run[r["run_id"]] if counts(p)]
            per_task.append({"side": n, "task": task, "runs": len(tr), "passed": sum(bool(r["passed"]) for r in tr),
                             "median_wall_s": statistics.median([r["wall_s"] for r in tr]),
                             "mean_requests": round(sum(r["requests"] for r in tr) / len(tr), 1),
                             "billed_usd": round(sum(billed(p, side_cfg[n]) for p in treq), 4),
                             "list_value_usd": round(sum(list_value(p, side_cfg[n]) for p in treq), 4)})

    paired = []
    for i, a_ in enumerate(present):
        for b_ in present[i + 1:]:
            keys = {(k[1], k[2]) for k in final if k[0] == a_} & {(k[1], k[2]) for k in final if k[0] == b_}
            pr = {"a": a_, "b": b_, "both": 0, "only_a": 0, "only_b": 0, "neither": 0, "n": len(keys)}
            for t, rp in keys:
                pa, pb = final[(a_, t, rp)]["passed"], final[(b_, t, rp)]["passed"]
                pr["both" if pa and pb else "only_a" if pa else "only_b" if pb else "neither"] += 1
            pr["sign_test_p"] = sign_test(pr["only_a"], pr["only_a"] + pr["only_b"])
            paired.append(pr)

    pf = sorted(out.glob("preflight-*.json"))
    json.dump({"sides": sides, "per_task": per_task, "paired": paired, "meters": meters},
              open(out / "summary.json", "w", encoding="utf-8"), indent=2)
    if per_task:
        with open(out / "per_task.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(per_task[0])); w.writeheader(); w.writerows(per_task)
    md = report(cfg, sides, per_task, paired, meters, pf[-1].name if pf else None)
    (out / "report.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"wrote {out / 'summary.json'}, {out / 'per_task.csv'}, {out / 'report.md'}")


if __name__ == "__main__":
    main()
