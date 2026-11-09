# Agent-suite results

_Generated 2026-11-08 19:01 from `results-pilot/`._

## Setup

| side | requested model | served model(s) | provider(s) | first request (UTC) | last request (UTC) |
|---|---|---|---|---|---|
| deepinfra | deepseek-ai/DeepSeek-V4.1-Flash-1017 | deepseek-ai/DeepSeek-V4.1-Flash-1017 | None | 2026-11-08T22:12 | 2026-11-08T22:57 |
| commandcode-goat | deepseek/deepseek-v4.1-flash | deepseek/deepseek-v4.1-flash | None | 2026-11-08T22:12 | 2026-11-08T22:57 |

Harness: `opencode run` with the same config on every side; agent timeout 1200s; tasks: 8.

Preflight: `preflight-20261108-221158.json`

## Headline

| metric | deepinfra | commandcode-goat |
|---|---|---|
| passed tasks per $10 | 7980.9 | 32215.8 |
| pass rate | 1.0 | 1.0 |
| pass rate 95% CI | [0.912, 1.0] | [0.912, 1.0] |
| graded runs | 40 | 40 |
| billed (own basis) | 0.0501 | 0.1242 |
| billing basis | reported_cost | credits |
| list-price value delivered | 0.0813 | 0.1242 |
| $10 buys this much list-price value (×) | 1.62 | 10.0 |
| billed per passed task | 0.0013 | 0.0031 |
| billed per graded run (mean) | 0.0013 | 0.0031 |
| billed per graded run 95% CI | [0.00115, 0.00138] | [0.00269, 0.00356] |
| plan $ per passed task |  | 0.0003 |
| projected passed tasks / month |  | 32215.8 |
| min weeks to use monthly credits |  | 2.0 |

_Pay-as-you-go: "per $10" is what this run actually spent. Subscription: "per $10" assumes the month's full credit allowance gets used at the credits-per-passed-task rate measured here; it can't be used faster than the weekly cap allows. "Billed" is in each side's own currency: provider-reported dollars, or plan credits (tokens × the plan's per-model rate, doubled in peak hours)._

## Tokens and caching

| metric | deepinfra | commandcode-goat |
|---|---|---|
| requests | 256 | 282 |
| mean_requests_per_run | 6.4 | 7.0 |
| prompt_tokens | 1989141 | 2460372 |
| cached_tokens | 1670528 | 2040960 |
| cache_hit_rate | 0.84 | 0.83 |
| output_tokens | 47566 | 91880 |
| reasoning_tokens | 0 | 28909 |
| mean_prompt_tokens_per_run | 49729 | 61509 |
| peak_request_share | 0.0 | 0.0 |

## Speed

| metric | deepinfra | commandcode-goat |
|---|---|---|
| median_ttft_s | 0.697 | 1.373 |
| p90_ttft_s | 1.283 | 1.593 |
| median_headers_s | 0.338 | 1.363 |
| median_request_latency_s | 1.091 | 1.878 |
| median_output_tok_per_s | 231.881 | 279.563 |
| median_wall_s_per_run | 54.75 | 71.95 |

## Reliability

| metric | deepinfra | commandcode-goat |
|---|---|---|
| tool_calls | 203 | 314 |
| malformed_tool_calls | 0 | 0 |
| malformed_tool_call_rate | 0.0 | 0.0 |
| agent_timeouts | 0 | 0 |
| runs_cut_off_by_cap | 0 | 0 |
| cap_responses | 0 | 0 |
| rate_limited_responses | 0 | 0 |
| other_errors | 0 | 0 |
| billed_missing_reported_cost | 0 | 0 |

## Usage windows: commandcode-goat

| 5h window opened (UTC) | requests | credits used | list value | capped at |
|---|---|---|---|---|
| 2026-11-08T22:12 | 282 | $0.1242 | $0.1242 |  |

| 7-day window opened (UTC) | requests | credits used | capped at |
|---|---|---|---|
| 2026-11-08T22:12 | 282 | $0.1242 |  |

## Paired outcomes (same task, same repeat, both sides graded)

| pair (A vs B) | both passed | only A | only B | neither | pairs | sign test p (discordant pairs) |
|---|---|---|---|---|---|---|
| deepinfra vs commandcode-goat | 40 | 0 | 0 | 0 | 40 |  |

## Pass rate by task group

| group (pass rate, 95% CI) | deepinfra | commandcode-goat |
|---|---|---|
| core (8 tasks) | 40/40 = 1.00 [0.912, 1.0] | 40/40 = 1.00 [0.912, 1.0] |
| hard (5 tasks) | - | - |

## Per task

| task | deepinfra (passed · billed/run · median wall) | commandcode-goat (passed · billed/run · median wall) |
|---|---|---|
| t01_tags | 5/5 · $0.0010/run · 68.5s | 5/5 · $0.0018/run · 50.9s |
| t02_split_bug | 5/5 · $0.0010/run · 87.7s | 5/5 · $0.0021/run · 63.9s |
| t03_csv_quotes | 5/5 · $0.0010/run · 36.5s | 5/5 · $0.0034/run · 72.7s |
| t04_refactor_report | 5/5 · $0.0011/run · 43.6s | 5/5 · $0.0027/run · 80.0s |
| t05_write_tests | 5/5 · $0.0020/run · 61.6s | 5/5 · $0.0055/run · 93.7s |
| t06_currency | 5/5 · $0.0016/run · 61.6s | 5/5 · $0.0047/run · 104.8s |
| t07_cli_balance | 5/5 · $0.0012/run · 52.4s | 5/5 · $0.0027/run · 67.8s |
| t08_dedupe_perf | 5/5 · $0.0011/run · 60.0s | 5/5 · $0.0019/run · 61.0s |
