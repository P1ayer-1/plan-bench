# Agent-suite results

_Generated 2026-11-09 02:12 from `results/`._

## Setup

| side | requested model | served model(s) | provider(s) | first request (UTC) | last request (UTC) |
|---|---|---|---|---|---|
| deepinfra | deepseek-ai/DeepSeek-V4.1-Flash-1017 | deepseek-ai/DeepSeek-V4.1-Flash-1017 | None | 2026-11-09T00:15 | 2026-11-09T02:08 |
| deepinfra-reasoning | deepseek-ai/DeepSeek-V4.1-Flash-1017 | deepseek-ai/DeepSeek-V4.1-Flash-1017 | None | 2026-11-09T00:15 | 2026-11-09T02:01 |
| commandcode-goat | deepseek/deepseek-v4.1-flash | deepseek/deepseek-v4.1-flash | None | 2026-11-09T00:15 | 2026-11-09T02:02 |
| commandcode-goat-noreasoning | deepseek/deepseek-v4.1-flash | deepseek/deepseek-v4.1-flash | None | 2026-11-09T00:15 | 2026-11-09T02:02 |

Harness: `opencode run` with the same config on every side; agent timeout 1200s; tasks: 13.

Preflight: `preflight-20261109-001424.json`

## Headline

| metric | deepinfra | deepinfra-reasoning | commandcode-goat | commandcode-goat-noreasoning |
|---|---|---|---|---|
| passed tasks per $10 | 2698.0 | 3529.8 | 12052.2 | 16772.2 |
| pass rate | 0.908 | 1.0 | 0.985 | 0.923 |
| pass rate 95% CI | [0.813, 0.957] | [0.944, 1.0] | [0.918, 0.997] | [0.832, 0.967] |
| graded runs | 65 | 65 | 65 | 65 |
| billed (own basis) | 0.2187 | 0.1841 | 0.531 | 0.3577 |
| billing basis | reported_cost | reported_cost | credits | credits |
| list-price value delivered | 0.3381 | 0.3259 | 0.3365 | 0.2251 |
| $10 buys this much list-price value (×) | 1.55 | 1.77 | 6.34 | 6.29 |
| billed per passed task | 0.0037 | 0.0028 | 0.0083 | 0.006 |
| billed per graded run (mean) | 0.0034 | 0.0028 | 0.0082 | 0.0055 |
| billed per graded run 95% CI | [0.00195, 0.00521] | [0.00241, 0.0033] | [0.00646, 0.01011] | [0.00438, 0.00679] |
| plan $ per passed task |  |  | 0.0008 | 0.0006 |
| projected passed tasks / month |  |  | 12052.2 | 16772.2 |
| min weeks to use monthly credits |  |  | 2.0 | 2.0 |

_Pay-as-you-go: "per $10" is what this run actually spent. Subscription: "per $10" assumes the month's full credit allowance gets used at the credits-per-passed-task rate measured here; it can't be used faster than the weekly cap allows. "Billed" is in each side's own currency: provider-reported dollars, or plan credits (tokens × the plan's per-model rate, doubled in peak hours)._

## Tokens and caching

| metric | deepinfra | deepinfra-reasoning | commandcode-goat | commandcode-goat-noreasoning |
|---|---|---|---|---|
| requests | 1100 | 617 | 538 | 608 |
| mean_requests_per_run | 16.9 | 9.5 | 8.3 | 9.4 |
| prompt_tokens | 25183393 | 7368900 | 6005343 | 6361186 |
| cached_tokens | 24488320 | 6777600 | 5126272 | 5550848 |
| cache_hit_rate | 0.972 | 0.92 | 0.854 | 0.873 |
| output_tokens | 267243 | 361469 | 315455 | 144774 |
| reasoning_tokens | 0 | 209809 | 172688 | 0 |
| mean_prompt_tokens_per_run | 387437 | 113368 | 92390 | 97864 |
| peak_request_share | 0.0 | 0.0 | 0.561 | 0.571 |

## Speed

| metric | deepinfra | deepinfra-reasoning | commandcode-goat | commandcode-goat-noreasoning |
|---|---|---|---|---|
| median_ttft_s | 0.792 | 0.722 | 1.407 | 1.414 |
| p90_ttft_s | 1.633 | 1.126 | 1.68 | 1.702 |
| median_headers_s | 0.435 | 0.378 | 1.397 | 1.39 |
| median_request_latency_s | 1.714 | 1.847 | 2.269 | 1.841 |
| median_output_tok_per_s | 225.534 | 185.525 | 234.0 | 291.177 |
| median_wall_s_per_run | 65.5 | 94.3 | 86.0 | 70.6 |

## Reliability

| metric | deepinfra | deepinfra-reasoning | commandcode-goat | commandcode-goat-noreasoning |
|---|---|---|---|---|
| tool_calls | 1010 | 627 | 542 | 502 |
| malformed_tool_calls | 0 | 0 | 0 | 0 |
| malformed_tool_call_rate | 0.0 | 0.0 | 0.0 | 0.0 |
| agent_timeouts | 4 | 0 | 0 | 0 |
| runs_cut_off_by_cap | 0 | 0 | 0 | 0 |
| cap_responses | 0 | 0 | 0 | 0 |
| rate_limited_responses | 0 | 0 | 0 | 0 |
| other_errors | 0 | 0 | 0 | 0 |
| billed_missing_reported_cost | 0 | 0 | 0 | 0 |

## Usage windows: commandcode-goat

| 5h window opened (UTC) | requests | credits used | list value | capped at |
|---|---|---|---|---|
| 2026-11-09T00:15 | 538 | $0.5310 | $0.3365 |  |

| 7-day window opened (UTC) | requests | credits used | capped at |
|---|---|---|---|
| 2026-11-09T00:15 | 538 | $0.5310 |  |

## Usage windows: commandcode-goat-noreasoning

| 5h window opened (UTC) | requests | credits used | list value | capped at |
|---|---|---|---|---|
| 2026-11-09T00:15 | 608 | $0.3577 | $0.2251 |  |

| 7-day window opened (UTC) | requests | credits used | capped at |
|---|---|---|---|
| 2026-11-09T00:15 | 608 | $0.3577 |  |

## Paired outcomes (same task, same repeat, both sides graded)

| pair (A vs B) | both passed | only A | only B | neither | pairs | sign test p (discordant pairs) |
|---|---|---|---|---|---|---|
| deepinfra vs deepinfra-reasoning | 59 | 0 | 6 | 0 | 65 | 0.0312 |
| deepinfra vs commandcode-goat | 58 | 1 | 6 | 0 | 65 | 0.125 |
| deepinfra vs commandcode-goat-noreasoning | 54 | 5 | 6 | 0 | 65 | 1.0 |
| deepinfra-reasoning vs commandcode-goat | 64 | 1 | 0 | 0 | 65 | 1.0 |
| deepinfra-reasoning vs commandcode-goat-noreasoning | 60 | 5 | 0 | 0 | 65 | 0.0625 |
| commandcode-goat vs commandcode-goat-noreasoning | 59 | 5 | 1 | 0 | 65 | 0.2188 |

## Pass rate by task group

| group (pass rate, 95% CI) | deepinfra | deepinfra-reasoning | commandcode-goat | commandcode-goat-noreasoning |
|---|---|---|---|---|
| core (8 tasks) | 40/40 = 1.00 [0.912, 1.0] | 40/40 = 1.00 [0.912, 1.0] | 39/40 = 0.97 [0.871, 0.996] | 39/40 = 0.97 [0.871, 0.996] |
| hard (5 tasks) | 19/25 = 0.76 [0.566, 0.885] | 25/25 = 1.00 [0.867, 1.0] | 25/25 = 1.00 [0.867, 1.0] | 21/25 = 0.84 [0.653, 0.936] |

## Per task

| task | deepinfra (passed · billed/run · median wall) | deepinfra-reasoning (passed · billed/run · median wall) | commandcode-goat (passed · billed/run · median wall) | commandcode-goat-noreasoning (passed · billed/run · median wall) |
|---|---|---|---|---|
| t01_tags | 5/5 · $0.0011/run · 93.8s | 5/5 · $0.0011/run · 69.4s | 5/5 · $0.0026/run · 61.7s | 5/5 · $0.0027/run · 73.5s |
| t02_split_bug | 5/5 · $0.0010/run · 65.5s | 5/5 · $0.0013/run · 71.7s | 5/5 · $0.0029/run · 75.5s | 5/5 · $0.0026/run · 91.5s |
| t03_csv_quotes | 5/5 · $0.0012/run · 49.0s | 5/5 · $0.0021/run · 86.6s | 4/5 · $0.0042/run · 59.1s | 4/5 · $0.0032/run · 90.9s |
| t04_refactor_report | 5/5 · $0.0011/run · 51.0s | 5/5 · $0.0017/run · 79.1s | 5/5 · $0.0031/run · 58.1s | 5/5 · $0.0030/run · 69.1s |
| t05_write_tests | 5/5 · $0.0019/run · 74.5s | 5/5 · $0.0026/run · 85.0s | 5/5 · $0.0079/run · 82.3s | 5/5 · $0.0062/run · 63.3s |
| t06_currency | 5/5 · $0.0019/run · 100.3s | 5/5 · $0.0028/run · 127.0s | 5/5 · $0.0065/run · 74.5s | 5/5 · $0.0048/run · 95.8s |
| t07_cli_balance | 5/5 · $0.0012/run · 51.3s | 5/5 · $0.0016/run · 65.4s | 5/5 · $0.0042/run · 77.5s | 5/5 · $0.0035/run · 55.7s |
| t08_dedupe_perf | 5/5 · $0.0010/run · 49.5s | 5/5 · $0.0011/run · 69.8s | 5/5 · $0.0034/run · 63.7s | 5/5 · $0.0032/run · 60.7s |
| t09_recurring | 4/5 · $0.0016/run · 78.8s | 5/5 · $0.0026/run · 93.1s | 5/5 · $0.0103/run · 100.3s | 5/5 · $0.0041/run · 50.0s |
| t10_query_dsl | 3/5 · $0.0072/run · 197.1s | 5/5 · $0.0070/run · 210.3s | 5/5 · $0.0218/run · 176.1s | 4/5 · $0.0120/run · 142.8s |
| t11_reconcile | 3/5 · $0.0158/run · 1200.2s | 5/5 · $0.0053/run · 184.0s | 5/5 · $0.0216/run · 179.5s | 4/5 · $0.0157/run · 184.0s |
| t12_fx_rates | 4/5 · $0.0075/run · 81.0s | 5/5 · $0.0047/run · 176.8s | 5/5 · $0.0103/run · 103.2s | 3/5 · $0.0064/run · 42.6s |
| t13_budget_rollover | 5/5 · $0.0013/run · 50.4s | 5/5 · $0.0030/run · 150.8s | 5/5 · $0.0074/run · 101.6s | 5/5 · $0.0042/run · 70.6s |
