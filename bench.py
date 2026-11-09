#!/usr/bin/env python3
"""
plan-bench: spend the same budget on two OpenAI-compatible endpoints
(e.g. OpenRouter pay-as-you-go vs a Command Code subscription), run the
same graded coding tasks on both, and log what you actually got.

Per request it logs: tokens (input / cached / output / reasoning),
list-price value of those tokens, latency, time-to-first-token,
pass/fail on the task's tests, and any rate-limit / cap errors.

Usage:
  export OPENROUTER_API_KEY=...  CMD_API_KEY=...
  python bench.py --config config.json --tasks tasks.jsonl --out results

Only standard library + `requests` needed:  pip install requests
"""
import argparse, csv, json, os, re, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

CSV_FIELDS = [
    "ts", "endpoint", "model", "round", "task_id", "status", "http_status",
    "prompt_tokens", "cached_tokens", "completion_tokens", "reasoning_tokens",
    "value_usd", "reported_cost_usd", "latency_s", "ttft_s", "passed", "error",
]


# ---------------------------------------------------------------- API call
def call_streaming(ep, task, timeout):
    """POST a streaming chat completion; return (text, usage, ttft, http_status)."""
    headers = {"Authorization": f"Bearer {os.environ[ep['api_key_env']]}",
               "Content-Type": "application/json"}
    headers.update(ep.get("extra_headers", {}))
    body = {
        "model": ep["model"],
        "messages": [
            {"role": "system", "content": task.get("system",
             "You are an expert Python programmer. Reply with one fenced ```python code block containing the full solution.")},
            {"role": "user", "content": task["prompt"]},
        ],
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    body.update(ep.get("extra_body", {}))  # temperature, max_tokens, provider pinning...

    t0 = time.monotonic()
    ttft, text, usage = None, [], None
    with requests.post(ep["base_url"].rstrip("/") + "/chat/completions",
                       headers=headers, json=body, stream=True, timeout=timeout) as r:
        if r.status_code != 200:
            return None, None, None, r.status_code, r.text[:500]
        for raw in r.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data:"):
                continue
            data = raw[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            if chunk.get("error"):
                return None, None, None, 200, json.dumps(chunk["error"])[:500]
            for ch in chunk.get("choices") or []:
                delta = ch.get("delta") or {}
                piece = delta.get("content") or ""
                if piece or delta.get("reasoning") or delta.get("reasoning_content"):
                    if ttft is None:
                        ttft = time.monotonic() - t0
                text.append(piece)
            if chunk.get("usage"):
                usage = chunk["usage"]
    return "".join(text), usage, ttft, 200, None


# ---------------------------------------------------------------- grading
CODE_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)

def grade(answer, task, timeout=20):
    """Run the model's code plus the task's asserts in an isolated subprocess."""
    blocks = CODE_RE.findall(answer or "")
    code = blocks[-1] if blocks else (answer or "")
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "solution_test.py"
        f.write_text(code + "\n\n# ---- tests ----\n" + task["tests"] + "\nprint('ALL_PASSED')\n")
        try:
            p = subprocess.run([sys.executable, "-I", str(f)], cwd=d, capture_output=True,
                               text=True, timeout=timeout)
            return p.returncode == 0 and "ALL_PASSED" in p.stdout
        except subprocess.TimeoutExpired:
            return False


# ---------------------------------------------------------------- pricing
def list_value(usage, price):
    """Value tokens at list price (USD per 1M). Cached input billed at cache rate."""
    pt = usage.get("prompt_tokens", 0) or 0
    ct = usage.get("completion_tokens", 0) or 0
    cached = ((usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)) or 0
    uncached = max(pt - cached, 0)
    return (uncached * price["input"] + cached * price.get("cached_input", price["input"])
            + ct * price["output"]) / 1e6


# ---------------------------------------------------------------- main loop
def run_endpoint(ep, tasks, cfg, writer, fh):
    name = ep["name"]
    spent, rounds, consecutive_caps = 0.0, 0, 0
    cap_events = []
    budget = ep.get("budget_value_usd", cfg.get("budget_value_usd", 10.0))
    max_rounds = cfg.get("max_rounds", 1000)
    wait = cfg.get("wait_on_cap_minutes", 0)
    print(f"\n=== {name} ({ep['model']}) — target value ${budget:.2f} ===")

    while rounds < max_rounds and spent < budget:
        rounds += 1
        for task in tasks:
            if spent >= budget:
                break
            t0 = time.monotonic()
            row = {"ts": datetime.now(timezone.utc).isoformat(), "endpoint": name,
                   "model": ep["model"], "round": rounds, "task_id": task["id"]}
            try:
                text, usage, ttft, status, err = call_streaming(ep, task, cfg.get("request_timeout_s", 600))
            except Exception as e:  # network error, timeout
                text, usage, ttft, status, err = None, None, None, -1, repr(e)[:500]
            row["latency_s"] = round(time.monotonic() - t0, 2)
            row["http_status"] = status

            if err is not None:
                capped = status in (402, 429) or re.search(r"limit|quota|credit|exceed", err, re.I)
                row.update(status="cap" if capped else "error", error=err)
                writer.writerow(row); fh.flush()
                print(f"  [{task['id']}] {row['status'].upper()} {status}: {err[:120]}")
                if capped:
                    consecutive_caps += 1
                    cap_events.append({"ts": row["ts"], "value_spent_so_far": round(spent, 4), "msg": err[:200]})
                    if wait and consecutive_caps <= cfg.get("max_cap_waits", 3):
                        print(f"  capped — sleeping {wait} min then retrying")
                        time.sleep(wait * 60)
                        continue
                    print("  capped — stopping this endpoint")
                    return spent, rounds, cap_events
                continue

            consecutive_caps = 0
            usage = usage or {}
            value = list_value(usage, ep["list_price"])
            spent += value
            passed = grade(text, task)
            row.update(
                status="ok",
                prompt_tokens=usage.get("prompt_tokens"),
                cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                value_usd=round(value, 6),
                reported_cost_usd=usage.get("cost"),  # OpenRouter returns real billed cost
                ttft_s=round(ttft, 2) if ttft is not None else None,
                passed=passed,
            )
            writer.writerow(row); fh.flush()
            print(f"  [{task['id']}] r{rounds} {'PASS' if passed else 'fail'}  "
                  f"in={row['prompt_tokens']} out={row['completion_tokens']}  "
                  f"${value:.4f}  total ${spent:.3f}")
            if cfg.get("sleep_between_s"):
                time.sleep(cfg["sleep_between_s"])
    return spent, rounds, cap_events


def summarize(csv_path, cap_log, out_path):
    rows = list(csv.DictReader(open(csv_path)))
    by = {}
    for r in rows:
        s = by.setdefault(r["endpoint"], {"requests": 0, "ok": 0, "passed": 0, "errors": 0, "caps": 0,
                                         "prompt": 0, "cached": 0, "output": 0, "value": 0.0,
                                         "reported_cost": 0.0, "latency": [], "ttft": []})
        s["requests"] += 1
        if r["status"] == "ok":
            s["ok"] += 1
            s["passed"] += r["passed"] == "True"
            s["prompt"] += int(r["prompt_tokens"] or 0)
            s["cached"] += int(r["cached_tokens"] or 0)
            s["output"] += int(r["completion_tokens"] or 0)
            s["value"] += float(r["value_usd"] or 0)
            s["reported_cost"] += float(r["reported_cost_usd"] or 0)
            s["latency"].append(float(r["latency_s"]))
            if r["ttft_s"]:
                s["ttft"].append(float(r["ttft_s"]))
        elif r["status"] == "cap":
            s["caps"] += 1
        else:
            s["errors"] += 1
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None
    summary = {}
    for k, s in by.items():
        summary[k] = {
            "requests": s["requests"], "successful": s["ok"],
            "pass_rate": round(s["passed"] / s["ok"], 3) if s["ok"] else None,
            "errors": s["errors"], "cap_hits": s["caps"],
            "prompt_tokens": s["prompt"], "cached_tokens": s["cached"], "output_tokens": s["output"],
            "cache_hit_rate": round(s["cached"] / s["prompt"], 3) if s["prompt"] else None,
            "list_price_value_usd": round(s["value"], 4),
            "openrouter_reported_cost_usd": round(s["reported_cost"], 4) or None,
            "median_latency_s": med(s["latency"]), "median_ttft_s": med(s["ttft"]),
            "cap_events": cap_log.get(k, []),
        }
    json.dump(summary, open(out_path, "w"), indent=2)
    print("\n================ SUMMARY ================")
    for k, s in summary.items():
        print(f"\n{k}")
        for kk, v in s.items():
            if kk != "cap_events":
                print(f"  {kk:30} {v}")
        print(f"  {'cap_events':30} {len(s['cap_events'])}")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--tasks", default="tasks.jsonl")
    ap.add_argument("--out", default="results")
    ap.add_argument("--only", help="run only this endpoint name")
    a = ap.parse_args()

    cfg = json.load(open(a.config))
    tasks = [json.loads(l) for l in open(a.tasks) if l.strip()]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    csv_path = out / f"requests-{stamp}.csv"

    eps = [e for e in cfg["endpoints"] if not a.only or e["name"] == a.only]
    for e in eps:
        if not os.environ.get(e["api_key_env"]):
            sys.exit(f"Missing env var {e['api_key_env']} for endpoint {e['name']}")

    cap_log = {}
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        w.writeheader()
        for e in eps:
            _, _, caps = run_endpoint(e, tasks, cfg, w, fh)
            cap_log[e["name"]] = caps
    summarize(csv_path, cap_log, out / f"summary-{stamp}.json")
    print(f"\nPer-request log: {csv_path}")


if __name__ == "__main__":
    main()
