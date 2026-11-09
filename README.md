# plan-bench

Spend the same budget on two OpenAI-compatible endpoints, run identical graded coding
tasks on both, and log what you actually got: tokens, list-price value, cache hits,
latency, pass rate, and when you hit caps.

> **For the agentic comparison ($10 OpenRouter credits vs the $10 Command Code GOAT plan), use
> [`agent-suite/`](agent-suite/README.md).** This root `bench.py` is the simpler single-shot harness.

## Setup

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

## Run

```bash
python bench.py                     # both endpoints
python bench.py --only openrouter   # one endpoint
```

Outputs go to `results/`:
- `requests-*.csv`: one row per request
- `summary-*.json`: totals per endpoint, including pass rate, cache hit rate, list-price value delivered, and cap events

## Config knobs (`config.json`)

| key | what it does |
|---|---|
| `budget_value_usd` | stop once this much **list-price value** has been consumed (set it to the plan's advertised value, e.g. 70 for Goat, to test the claim) |
| `max_rounds` | how many times to cycle the task set |
| `wait_on_cap_minutes` | on a 429/limit error, sleep and retry (e.g. 300 to wait out a 5-hour window); 0 = stop at first cap |
| `list_price` | USD per 1M tokens used to value usage. Use the model maker's official rates for both endpoints |
| `extra_body` | anything passed through: temperature, max_tokens, OpenRouter `provider` pinning |

## How to read the results

- **Value test:** `list_price_value_usd` = what the tokens you got would cost at list price.
  For Command Code, compare that against the $10 you paid and the "$70" claim, and note *when* the cap events happened.
- **Quality test:** `pass_rate` on identical tasks. Command Code may repair tool calls server-side;
  if its pass rate is higher, that's a real finding, not noise.
- **Caching:** report `cache_hit_rate`. Cached tokens are much cheaper, so a "$70" claim built
  mostly on cache reads means fewer real tokens than it sounds like.
- `openrouter_reported_cost_usd` is OpenRouter's actual billed cost, a good sanity check on the
  list-price math.

## Before publishing anything

- **Write your own held-out tasks.** The 8 sample tasks in `tasks.jsonl` are for smoke-testing the
  harness only; tasks like these are likely in training data. Aim for 50+ for a real result.
- **Run each side more than once**, on different days, and report the spread.
- **Safety:** grading executes model-written code. Run this in a container or VM.
- Publish the method, tasks (or a hashed version of them), and raw CSVs, and describe results neutrally.
