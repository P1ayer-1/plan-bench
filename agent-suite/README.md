# agent-suite

Agentic benchmark for one question: **what does $10 buy for agentic coding: $10 of prepaid API credits,
or a $10/month Command Code GOAT plan?** Both routes serve DeepSeek V4.1 Flash. The same harness (opencode
1.19.5) runs the same tasks on each, and a logging proxy records what each route delivers and charges.

The API route is DeepInfra direct. It serves the 1017 snapshot at the same per-token price as OpenRouter
pinned to DeepInfra, without OpenRouter's fee on buying credits. Command Code turns reasoning on by
default and DeepInfra doesn't, so each route also runs with reasoning switched the other way. That gives
a 2×2 design:

| side | route | reasoning |
|---|---|---|
| `deepinfra` | DeepInfra | off (its default) |
| `deepinfra-reasoning` | DeepInfra | `reasoning_effort: medium` |
| `commandcode-goat` | Command Code GOAT | on (its default) |
| `commandcode-goat-noreasoning` | Command Code GOAT | `reasoning_effort: off` |

```
opencode ──> proxy.py ──> /<side>/run/<run_id>/v1 ──> DeepInfra or Command Code (OpenAI-compatible)
```

## Files

| file | what it is |
|---|---|
| `preflight.py` | live checks per side: key, model listed, served model + provider, tool call validity, usage/cost fields, prompt caching |
| `proxy.py` | pass-through proxy; injects real keys and `inject_body` params, logs tokens / cache / latency / TTFT / time to headers / tool-call validity / served model, classifies errors as `cap` / `rate_limit` / `error` |
| `run_suite.py` | runs tasks on every side in fresh copies of `sandbox/` (lockstep scheduler, budgets, cap waits, `--workers`, `--resume`), then grades |
| `analyze.py` | `summary.json`, `per_task.csv`, and `report.md`: headline, bootstrap CIs, tokens, speed, reliability, usage windows, pairwise outcomes, pass rate by task group, per task |
| `costs.py` | list value, billed cost (reported cost, or plan credits with peak-hour multiplier), cap classification, rolling-window replay |
| `config.py` | config loader; supports `"extends"` so variant configs only hold overrides |
| `grading.py` / `validate.py` | hidden-test grading; validator: every task FAILS on the sandbox and PASSES with its reference |
| `suite_config.json` | the main comparison: 4 sides × 13 tasks × 5 rounds |
| `pilot_config.json` | re-analyzes the first run (2 sides × 8 core tasks, `results-pilot/`) |
| `smoke_config.json` | writes to `results-smoke/`, for trial runs |
| `capprobe_config.json` | Command Code alone, until it hits its caps (impractical on a cheap model; see below) |
| `run.sh`, `Dockerfile` | one-shot pipeline, and the container it runs in |
| `dev/mock_llm.py`, `dev/mock_config.json` | offline end-to-end test: fake pay-as-you-go API + fake capped Command Code |

## Tasks

All tasks work on a small Python personal-finance library (`sandbox/ledger`). Each is graded by hidden tests
the agent never sees.

| task | group | what it asks |
|---|---|---|
| t01_tags | core | feature: tag filter |
| t02_split_bug | core | bug fix: rounding in `Money.split` |
| t03_csv_quotes | core | bug fix: CSV quoting, CRLF, error line numbers |
| t04_refactor_report | core | refactor + new function, same behaviour |
| t05_write_tests | core | write tests; graded by killing ≥5 of 6 planted mutants |
| t06_currency | core | multi-file change: currency safety across money/ledger/report/CLI |
| t07_cli_balance | core | CLI command with exact output and exit codes |
| t08_dedupe_perf | core | performance: 200k rows in under 2 s, same semantics |
| t09_recurring | hard | recurring transactions: month-end anchoring, leap years, count/until/skip |
| t10_query_dsl | hard | a search language: tokenizer, precedence, implicit AND, quoting, errors |
| t11_reconcile | hard | bank reconciliation: max matching then min total date distance (greedy fails) |
| t12_fx_rates | hard | historical FX: effective dates, inverses, USD triangulation, round once |
| t13_budget_rollover | hard | budgets with rollover, caps, refunds, month ranges, validation |

The hard tasks' hidden tests were checked against plausible wrong solutions: greedy matching, rounding per
transaction, and chained month clamping all fail.

## How the routes are charged

| | DeepInfra | Command Code GOAT |
|---|---|---|
| model | `deepseek-ai/DeepSeek-V4.1-Flash-1017` | `deepseek/deepseek-v4.1-flash` ("latest"; no snapshot date reported) |
| "spent" | `usage.estimated_cost` reported by DeepInfra (real dollars; 51%-off promo at run time) | plan credits = tokens × $0.15 / $0.60 / $0.003 per M (in / out / cache read), **×2 in peak hours** (01–04 and 06–10 UTC, Mon–Fri) |
| per $10 | passed tasks per $10 spent | $100 monthly credits ÷ credits per passed task (up to $20 per 5 h, $50 per week) |

Every side is also valued at one shared yardstick, `list_price` (DeepSeek's official rates), as "list-price value delivered".

## Running it

**Accounts.** DeepInfra: top up, use a dedicated key, and note the balance before and after. Command Code: GOAT
subscription with **auto-reload off and no extra credits** (extra credits are spent first while a window is
capped, so caps never show and you get billed). Note Studio > Usage before and after.

**Container** (agents get unattended shell access):
```bash
docker build -t plan-bench-agent .
docker run --rm -v "$PWD:/suite" -e DEEPINFRA_API_KEY -e CMD_API_KEY plan-bench-agent bash run.sh --workers 6
```
`run.sh` = preflight → proxy → `run_suite.py` → `analyze.py`. Useful flags: `--tasks t01_tags,t11_reconcile`,
`--repeats 1`, `--sides deepinfra,commandcode-goat`, `--resume` (skip finished jobs after a restart),
`CONFIG=smoke_config.json` for trial runs. Afterwards, record the dashboard meter:
`python analyze.py --meter commandcode-goat=<Studio dollars>`.

All sides run the same (round, task) jobs in lockstep, so time of day and load hit them equally. Spending the
full $10 isn't practical: an agent task costs about $0.001–0.01. The report therefore projects "passed tasks per
$10" from the measured cost per passed task, and `budget_usd` / `stop_together` stay as safety stops.

**Cap probe** (`capprobe_config.json`): on DeepSeek V4.1 Flash the $20/5 h window is thousands of agent tasks,
far more than a few workers can run in 5 hours. When a cap does trigger, the runner sleeps until the reset time
in the cap message, then resumes. It stops at the weekly cap.

## Outputs (`results/`)

- `report.md`, `summary.json`, `per_task.csv`
- `results.jsonl`: one row per run. `proxy_log.jsonl`: one row per API request. `preflight-*.json`.
- `runs/<run_id>/`: `prompt.txt`, `agent.diff`, agent stdout/stderr, `grade.txt`. Workspaces are not committed.

A run cut off by a cap is re-run once the window resets; the cut-off attempt is left out of the pass rate,
but its tokens still count toward cost.

## Offline test (no keys, no spend)

```bash
python dev/mock_llm.py 10 60 &          # fake endpoints; /cc caps after 10 requests for 60 s
MOCK_API_KEY=x python proxy.py --config dev/mock_config.json &
python run_suite.py --config dev/mock_config.json --workers 2
python analyze.py --config dev/mock_config.json
```

## Notes

- **Windows:** prompts go to opencode on stdin; long quoted prompts passed through argv reach opencode.exe
  re-escaped, and npm's `.cmd` shim strips quotes. The runner follows the shim to the real `.exe`. Git calls
  pass `-c safe.directory=*` for drives that don't record file ownership.
- **Isolation:** per-run XDG state/data dirs; empty shared config/cache dirs; `--pure` disables plugins;
  `*_API_KEY` env vars are removed from the agent's environment, so only the proxy holds keys.
- **Adding tasks:** `tasks/tNN_name/task.md` + `hidden_test.py` (or `grade.py`), reference in
  `validation/refs/tNN_name/`, add it to a `task_groups` entry, then `python validate.py`.
