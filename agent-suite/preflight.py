#!/usr/bin/env python3
"""
Pre-run checks against the real endpoints (costs well under a cent per side):

  1. the key works and the model ID is listed
  2. a streamed tool call comes back, with valid JSON arguments
  3. which model/provider the upstream says served it (snapshot + provider pinning check)
  4. usage arrives in the stream (prompt / cached / reasoning tokens, `cost` if reported)
  5. prompt caching: two requests with the same ~3k-token prefix; the second should show cached tokens

Writes results/preflight-<stamp>.json so the run's setup is on record for the write-up.

  python preflight.py --config suite_config.json [--sides a,b]
"""
import argparse, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path

import requests
from config import load_config

ROOT = Path(__file__).parent
TOOL = {"type": "function", "function": {
    "name": "read_file", "description": "Read a file from the workspace",
    "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}
# deterministic ~3k-token prefix so prompt caching has something to hit
PREFIX = "Reference notes for the ledger project (ignore unless asked):\n" + "\n".join(
    f"- note {i}: the ledger module keeps transactions sorted by date; amounts are Decimal; id {i * 7919 % 10007}"
    for i in range(160))


def stream(side, messages, tools=None, max_tokens=300):
    body = {"model": side["model"], "messages": messages, "stream": True,
            "stream_options": {"include_usage": True}, "max_tokens": max_tokens}
    if tools:
        body["tools"] = tools
    for k, v in side.get("inject_body", {}).items():
        body.setdefault(k, v)
    h = {"Authorization": "Bearer " + os.environ[side["api_key_env"]], "Content-Type": "application/json"}
    t0 = time.monotonic()
    out = {"status": None, "text": "", "tool_args": {}, "tool_names": {}, "usage": None, "model": None,
           "provider": None, "ttft_s": None, "error": None}
    with requests.post(side["base_url"].rstrip("/") + "/chat/completions", headers=h, json=body,
                       stream=True, timeout=120) as r:
        out["status"] = r.status_code
        if r.status_code != 200:
            out["error"] = r.text[:400]
            return out
        for raw in r.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data:"):
                continue
            data = raw[5:].strip()
            if data == "[DONE]":
                break
            try:
                c = json.loads(data)
            except json.JSONDecodeError:
                continue
            if c.get("error"):
                out["error"] = json.dumps(c["error"])[:400]
            out["model"] = c.get("model") or out["model"]
            out["provider"] = c.get("provider") or out["provider"]
            for ch in c.get("choices") or []:
                d = ch.get("delta") or {}
                if out["ttft_s"] is None and (d.get("content") or d.get("tool_calls") or d.get("reasoning")
                                              or d.get("reasoning_content")):
                    out["ttft_s"] = round(time.monotonic() - t0, 2)
                out["text"] += d.get("content") or ""
                for tc in d.get("tool_calls") or []:
                    i = tc.get("index", 0)
                    fn = tc.get("function") or {}
                    out["tool_args"][i] = out["tool_args"].get(i, "") + (fn.get("arguments") or "")
                    if fn.get("name"):
                        out["tool_names"][i] = fn["name"]
            if c.get("usage"):
                out["usage"] = c["usage"]
    out["latency_s"] = round(time.monotonic() - t0, 2)
    return out


def usage_line(u):
    if not u:
        return "NO USAGE IN STREAM"
    det = u.get("prompt_tokens_details") or {}
    cdet = u.get("completion_tokens_details") or {}
    return (f"prompt={u.get('prompt_tokens')} cached={det.get('cached_tokens')} "
            f"completion={u.get('completion_tokens')} reasoning={cdet.get('reasoning_tokens')} cost={u.get('cost', u.get('estimated_cost'))}")


def check(side):
    rep, problems = {"side": side["name"], "model": side["model"]}, []
    h = {"Authorization": "Bearer " + os.environ[side["api_key_env"]]}
    try:
        ids = [m["id"] for m in requests.get(side["base_url"].rstrip("/") + "/models", headers=h, timeout=30).json()["data"]]
        rep["model_listed"] = side["model"] in ids
        if not rep["model_listed"]:
            problems.append(f"model {side['model']} not in /models")
    except Exception as e:
        rep["model_listed"] = None
        problems.append(f"/models failed: {e!r}")

    sys_msg = {"role": "system", "content": "You are a coding agent. Use tools when asked."}
    t = stream(side, [sys_msg, {"role": "user", "content": "Read the file ledger/money.py using the read_file tool."}],
               tools=[TOOL])
    rep["tool_call"] = {k: t[k] for k in ("status", "model", "provider", "ttft_s", "latency_s", "error") if k in t}
    rep["tool_call"]["usage"] = t["usage"]
    args = list(t["tool_args"].values())
    rep["tool_call"]["calls"] = [{"name": t["tool_names"].get(i), "args": a} for i, a in t["tool_args"].items()]
    if t["status"] != 200 or t["error"]:
        problems.append(f"tool-call request failed: {t['status']} {t['error']}")
    elif not args:
        problems.append("no tool call returned")
    else:
        for a in args:
            try:
                json.loads(a or "{}")
            except json.JSONDecodeError:
                problems.append(f"malformed tool args: {a[:80]}")
    if t["status"] == 200 and not t["usage"]:
        problems.append("no usage block in the stream")

    caching = []
    for i in range(2):
        c = stream(side, [{"role": "system", "content": PREFIX},
                          {"role": "user", "content": f"Reply with just the word ok. ({i})"}], max_tokens=20)
        caching.append({"status": c["status"], "usage": c["usage"], "provider": c["provider"], "error": c["error"]})
        time.sleep(2)
    rep["caching"] = caching
    second = ((caching[1].get("usage") or {}).get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    rep["cache_hit_on_repeat"] = second > 0
    if not second:
        problems.append("no cached tokens on an identical ~3k-token prefix (caching off, or not reported)")
    if side.get("billing", {}).get("basis") == "reported_cost" and (t["usage"] or {}).get("cost", (t["usage"] or {}).get("estimated_cost")) is None:
        problems.append("billing basis is reported_cost but the response has no usage.cost")
    rep["problems"] = problems

    print(f"\n== {side['name']}  ({side['model']})")
    print(f"  listed in /models : {rep['model_listed']}")
    print(f"  served model      : {t['model']}   provider: {t['provider']}")
    print(f"  tool call         : {rep['tool_call']['calls'] or t['text'][:80]!r}  ttft={t['ttft_s']}s")
    print(f"  tool-call usage   : {usage_line(t['usage'])}")
    for i, c in enumerate(caching):
        print(f"  cache probe {i + 1}     : {usage_line(c['usage'])}  provider={c['provider']}")
    print("  " + ("OK" if not problems else "PROBLEMS:\n    - " + "\n    - ".join(problems)))
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="suite_config.json")
    ap.add_argument("--sides")
    a = ap.parse_args()
    cfg = load_config(a.config)
    sides = [s for s in cfg["sides"] if not a.sides or s["name"] in a.sides.split(",")]
    reports = []
    for s in sides:
        if not os.environ.get(s["api_key_env"]):
            print(f"\n== {s['name']}: SKIPPED, {s['api_key_env']} not set")
            reports.append({"side": s["name"], "skipped": True})
            continue
        reports.append(check(s))
    served = {r["side"]: (r.get("tool_call") or {}).get("model") for r in reports if not r.get("skipped")}
    if len(set(served.values())) > 1:
        print(f"\nNOTE: sides report different served model IDs: {served}. Confirm they are the same snapshot.")
    out = ROOT / cfg["results_dir"]; out.mkdir(parents=True, exist_ok=True)
    path = out / f"preflight-{datetime.now():%Y%m%d-%H%M%S}.json"
    json.dump({"ts": datetime.now(timezone.utc).isoformat(), "reports": reports}, open(path, "w", encoding="utf-8"), indent=2)
    print(f"\nwrote {path}")
    sys.exit(1 if any(r.get("problems") for r in reports) else 0)


if __name__ == "__main__":
    main()
