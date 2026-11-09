# plan-bench

**What does $10 buy for agentic coding: prepaid API credits, or a $10/month coding plan?** This repo runs the same
coding agent (opencode) on the same graded tasks against several OpenAI-compatible endpoints serving the same
model, through a logging proxy that records what each one delivers and charges: tokens, cache hits, latency,
tool-call health, billed cost, and plan caps.

- **Write-up:** [`writeup/blog_post.md`](writeup/blog_post.md)
- **Main results:** [`agent-suite/results/report.md`](agent-suite/results/report.md) (4 sides × 13 tasks × 5 rounds, 2026-11-09)
- **Pilot:** [`agent-suite/results-pilot/report.md`](agent-suite/results-pilot/report.md) (2 sides × 8 tasks × 5 rounds, 2026-11-08)
- **Harness and how to rerun it:** [`agent-suite/`](agent-suite/README.md)

## Results in brief (DeepSeek V4.1 Flash, Nov 2026)

| | DeepInfra API, reasoning off | DeepInfra API, reasoning on | Command Code GOAT, reasoning on | Command Code GOAT, reasoning off |
|---|---|---|---|---|
| hard tasks passed | 19/25 | 25/25 | 25/25 | 21/25 |
| all tasks passed | 59/65 | 65/65 | 64/65 | 60/65 |
| charged per passed task | $0.0037 | $0.0028 | $0.0083 plan credit | $0.0060 plan credit |
| passed tasks per $10 | ~2,700 | ~3,500 | ~12,000/month if fully used | ~16,800/month if fully used |
| median time to first token | 0.79 s | 0.72 s | 1.41 s | 1.41 s |

Reasoning decided quality; the route didn't. The $10/month plan is worth it for daily agent use: once you'd spend
more than $10 a month on the API, it buys 3–5× more work per dollar (break-even ~120 tasks a day at this benchmark's
task size, roughly 12–25 a day for real-codebase sessions). For occasional use, $10 of API credit is cheaper. No caps, rate limits or malformed tool calls in 2,863 requests.
Details and caveats are in the write-up.

## Single-shot harness (`bench.py`, older)

The root `bench.py` is a simpler, non-agentic harness: one prompt per task, graded by asserts. It shares no code
with `agent-suite/`.

### Setup

```bash
pip install requests
export OPENROUTER_API_KEY=sk-or-...
export CMD_API_KEY=...            # from Command Code Studio
```

Check the exact model IDs on each side first; the IDs in `config.json` are placeholders:

```bash
curl -s https://api.commandcode.ai/provider/v1/models -H "Authorization: Bearer $CMD_API_KEY"
```

Use the **same model** on both endpoints so you're comparing plans, not models.

### Run

```bash
python bench.py                     # both endpoints
python bench.py --only openrouter   # one endpoint
```

Outputs go to `results/`:
- `requests-*.csv`: one row per request
- `summary-*.json`: totals per endpoint, including pass rate, cache hit rate, list-price value delivered, and cap events

### Config knobs (`config.json`)

| key | what it does |
|---|---|
| `budget_value_usd` | stop once this much **list-price value** has been consumed (set it to the plan's advertised value, e.g. 70 for Goat, to test the claim) |
| `max_rounds` | how many times to cycle the task set |
| `wait_on_cap_minutes` | on a 429/limit error, sleep and retry (e.g. 300 to wait out a 5-hour window); 0 = stop at first cap |
| `list_price` | USD per 1M tokens used to value usage. Use the model maker's official rates for both endpoints |
| `extra_body` | anything passed through: temperature, max_tokens, OpenRouter `provider` pinning |

### How to read the results

- **Value test:** `list_price_value_usd` = what the tokens you got would cost at list price.
  For Command Code, compare that against the $10 you paid and the "$70" claim, and note *when* the cap events happened.
- **Quality test:** `pass_rate` on identical tasks. Command Code may repair tool calls server-side;
  if its pass rate is higher, that's a real finding, not noise.
- **Caching:** report `cache_hit_rate`. Cached tokens are much cheaper, so a "$70" claim built
  mostly on cache reads means fewer real tokens than it sounds like.
- `openrouter_reported_cost_usd` is OpenRouter's actual billed cost, a good sanity check on the
  list-price math.

### Before publishing anything

- **Write your own held-out tasks.** The 8 sample tasks in `tasks.jsonl` are for smoke-testing the
  harness only; tasks like these are likely in training data. Aim for 50+ for a real result.
- **Run each side more than once**, on different days, and report the spread.
- **Safety:** grading executes model-written code. Run this in a container or VM.
- Publish the method, tasks (or a hashed version of them), and raw CSVs, and describe results neutrally.
