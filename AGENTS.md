# AGENTS.md

This file provides guidance to Codex (claude.ai/code) when working with code in this repository.

## What this is

A benchmark asking what $10 buys: $10 of prepaid DeepInfra credits (direct API; same price as OpenRouter pinned to DeepInfra, minus OpenRouter's purchase fee) vs Command Code's $10/mo GOAT plan, with the **same model** (DeepSeek V4.1 Flash) on both. The main harness is **`agent-suite/`**, which is agentic: it drives the `opencode` CLI through tasks on a small `ledger` repo, with a logging proxy in between. Its README has the full run procedure. `writeup/blog_draft.md` is the blog post draft; its `[[...]]` placeholders get filled from `agent-suite/results/report.md` after a real run.

The root `bench.py` (single-shot chat completions graded by asserts, tasks in `tasks.jsonl`) is an older, separate harness. It shares no code with agent-suite and has its own pricing and cap logic.

Dependencies: Python stdlib + `requests` + `pytest`; opencode 1.19.5 (`npm i -g opencode-ai@1.19.5`). There is no build, lint, or package manifest. `agent-suite/Dockerfile` is the intended runtime, because agents run `--auto` with unattended shell access.

## Commands (from `agent-suite/`)

```bash
python validate.py                         # every task must FAIL on sandbox and PASS with its ref (~60s)
python preflight.py                        # live endpoint checks (keys, served model/provider, tool calls, caching, cost field)
bash run.sh [run_suite args]               # preflight -> proxy (bg) -> run_suite -> analyze
python proxy.py --config suite_config.json # or by hand: proxy in one terminal...
python run_suite.py --tasks t01_tags --repeats 1 --sides deepinfra   # ...single task / side
python analyze.py [--meter commandcode-goat=<studio $>]
```
Offline end-to-end test (no keys): `python dev/mock_llm.py 10 60 &`, `MOCK_API_KEY=x python proxy.py --config dev/mock_config.json &`, `python run_suite.py --config dev/mock_config.json --workers 2`. Sandbox tests: `cd sandbox && python -m pytest -q`.

## agent-suite architecture

- **Config** (`config.py`): JSON with optional `"extends"`. Overlays deep-merge, and `sides` merge by `name`. `capprobe_config.json` and `dev/mock_config.json` extend `suite_config.json`. All paths in a config resolve relative to `agent-suite/`.
- **`costs.py` is the single source of money math.** `list_value` = tokens × `list_price` (DeepSeek official; the same yardstick on every side). `billed` depends on the side's `billing.basis`: `reported_cost` (`usage.cost` on OpenRouter, `usage.estimated_cost` on DeepInfra, falling back to `fallback_price`), or `credits` (tokens × rate, × `peak.multiplier` when the request's UTC timestamp falls in peak hours). It also holds `classify_error` (per-side `cap_detection`: statuses and a message regex → `cap` / `rate_limit` / `error`; a 429 is a cap only if the message matches), `reset_seconds` (parses "Resets in 2h 41m"), and `windows` (replays rolling 5h/7d windows that open on first request).
- **`proxy.py`** routes `/<side>/run/<run_id>/v1/...` to the side's `base_url`, so the run tag lives in the URL and concurrent runs are attributed correctly. The older `/<side>/v1` + `POST /_tag` route still works. It replaces auth with the real key, merges `inject_body` via `setdefault` (client values win), forces `stream_options.include_usage`, and parses SSE in flight. It logs usage, TTFT, tool calls and malformed args, `served_model`/`provider`, and the error classification to `proxy_log.jsonl`.
- **`run_suite.py`**: a `Scheduler` hands out (round, task) jobs. The next job goes to the awake side with the fewest started jobs, so sides stay in lockstep. `--workers N` threads share it. A side stops at `budget_usd` (in its billing basis, read from the proxy log), at the end of its sequence, or at a cap. With `cap_policy.wait_on_cap_minutes` set, a capped side sleeps until the parsed reset time (giving up if it's more than `max_single_wait_hours` away), then re-runs the job the cap cut off. `stop_together` caps the other sides at the stopped side's job count, for paired comparisons. Each run gets a fresh `sandbox/` copy that is git-committed as the base, `opencode.json` rendered from `agent.config` (`{workspace}`/`{model}`/`{proxy_url}` placeholders), the prompt on **stdin** (`prompt.txt`), `*_API_KEY` stripped from the env, and per-run XDG state/data dirs.
- **`grading.py`**: `tasks/<t>/grade.py <ws>` if it exists (exit code is the result), otherwise `hidden_test.py` is copied in and run with pytest. It also records whether the visible `tests/` pass.
- **`analyze.py`** keeps the last non-capped attempt per (side, task, repeat). It computes per-side metrics, subscription projections from `plan`, window tables, paired outcomes with a sign test, and per-task numbers, and writes `summary.json`, `per_task.csv` and `report.md`.

## Gotchas

- Windows: never pass the prompt via argv. npm's `.cmd` shim strips quotes, and opencode.exe receives argv re-escaped. `resolve_exe` follows the shim to the real `.exe`. Git calls pass `-c safe.directory=*`.
- Tasks: `tasks/tNN_name/task.md` + `hidden_test.py` (or `grade.py`; t05 kills mutants and needs ≥5/6), with the reference in `validation/refs/tNN_name/` overlaid onto `sandbox/`. Refs must never reach workspaces. Rerun `validate.py` after touching tasks, refs, or `sandbox/`. Editing `sandbox/ledger/report.py` can break t05's exact-string mutants.
- `dev/mock_llm.py` identifies the task by the first 60 chars of the first line of `task.md`, so keep first lines distinctive.
- Command Code facts encoded in config (checked 2026-11-08, re-verify before a run): GOAT = $100/mo of DeepSeek V4.1 Flash usage, $20/5h, $50/week; $0.15/$0.60/$0.003 per M tokens, ×2 at 01–04 and 06–10 UTC Mon–Fri; extra credits bypass the windows. The DeepInfra prices in `fallback_price` are a 51%-off promo.
- As of 2026-11-08, only preflight has been run against a real API (DeepInfra: tool calls, cost, caching all OK). `CMD_API_KEY` was unset.
