# $10 of API credits vs a $10/month coding plan: what each buys for agentic coding

*Run on November 8, 2026. Prices and promos change; check them before relying on these numbers.*

**TL;DR:** I ran the same coding agent on the same 8 tasks, 40 runs per side, against DeepSeek V4.1 Flash
through two routes: DeepInfra's pay-as-you-go API, and Command Code's $10/month GOAT plan. Both passed
40/40. DeepInfra charged **$0.0013 per passed task**, so $10 covers about 8,000 tasks of this size. Command Code
used **$0.0031 of plan credit per task**, so the plan's $100 monthly allowance covers about 32,000 tasks,
roughly 4× as many per dollar. That only holds if you actually run ~1,000 agent tasks a day: below
roughly 8,000 tasks a month, the $10 of API credit costs less. Command Code was also slower per task (72 s vs 55 s
median) and turned on reasoning by default.

## The question

Command Code's GOAT plan costs $10 a month and advertises up to $100 of DeepSeek V4.1 Flash usage. The
alternative is to put $10 straight onto an inference provider and pay per token. "10× the value" only
counts if you can use it, so I measured what each route delivers for agentic coding:
tasks passed, cost per task, speed, and whether any limit kicks in.

## Setup

- **Model:** DeepSeek V4.1 Flash on both. DeepInfra serves the Oct 17 snapshot
  (`deepseek-ai/DeepSeek-V4.1-Flash-1017`). Command Code serves `deepseek/deepseek-v4.1-flash`, labelled
  "latest", and never reports a snapshot date, so I couldn't confirm it's the same weights.
- **Pay-as-you-go: DeepInfra, direct.** On the run date it had a 51% promo: $0.098 / $0.294 / $0.00294
  per million tokens (input / output / cached input), down from $0.20 / $0.60 / $0.006. OpenRouter routed to
  DeepInfra charges the same per token, plus a fee when you buy credits, so going direct is the cheaper way
  to spend $10 on API credit.
- **Subscription: Command Code GOAT**, $10/month. For DeepSeek V4.1 Flash it includes up to $100 of usage
  a month, at most $20 in any 5 hours and $50 in any 7 days. Usage is charged at $0.15 / $0.60 / $0.003
  per million tokens, doubled in weekday peak hours (01–04 and 06–10 UTC). The whole run fell on a Sunday
  evening (UTC), so every request was off-peak.
- **Agent:** opencode 1.19.5, run unattended (`opencode run --auto`) in a Docker container, with
  identical configuration on both sides. A logging proxy sat between the agent and each API and recorded every
  request's tokens, cache hits, latency, tool calls and errors.
- **Tasks:** 8 tasks on a small Python personal-finance library: a feature, two bug fixes, a refactor,
  writing tests (graded by how many planted bugs the tests catch), a multi-file currency change, a CLI
  command with exact output, and a performance fix. Each is graded by hidden tests the agent never sees.
- **Procedure:** 5 rounds of all 8 tasks per side (40 runs each). The two sides ran in lockstep, so both
  were always under the same load at the same moment. 22:12–22:57 UTC.

## Results

### What $10 buys

| | DeepInfra ($10 prepaid) | Command Code GOAT ($10/mo) |
|---|---|---|
| tasks passed | 40 / 40 | 40 / 40 |
| charged for the run | $0.050 | $0.124 of plan credit |
| per passed task | $0.0013 | $0.0031 credit (= $0.0003 of the $10 fee, if you use the whole allowance) |
| passed tasks per $10 | ~8,000 | ~32,000 per month, if fully used |
| list-price value per $10* | 1.6× | 10× |

\*Every token valued at DeepSeek's official rates ($0.15 / $0.60 / $0.003). DeepInfra's promo makes $10 worth
$16 at list price. Command Code's plan is worth $100, if you use it all.

Per dollar, the subscription buys about 4× as many tasks, but the dollars arrive differently: GOAT
charges $10 every month whether you use it or not, while DeepInfra charges only for what you use. At this
run's cost per task, the break-even is about **8,000 agent tasks a month (~270 a day)**. Below that, the
$10 of API credit is cheaper and lasts longer than a month. Above it, the plan wins, up to its caps.

### The caps don't bind

The whole run used $0.12 of Command Code credit. The 5-hour window holds $20, about 6,400 of these tasks,
or more than 20 a minute for 5 hours straight. One agent working sequentially takes about a minute per task. On a model
this cheap, the rolling windows aren't a real constraint for one developer. The binding limit is the $100 monthly
allowance, which you'd need about two weeks of nonstop agent use to exhaust (the weekly cap is $50).

The time-of-day pricing matters more than the caps. A US developer working 9–5 Eastern never touches
peak hours, but someone in Asia working daytime hours sits in the 01–04 and 06–10 UTC windows, and every request
there costs double.

### Same model, different behaviour

On paper both sides serve the same model. In practice they behaved differently:

| per run (median or mean) | DeepInfra | Command Code |
|---|---|---|
| requests | 6.4 | 7.0 |
| prompt tokens | 49,700 | 61,500 |
| output tokens | 1,190 | 2,300 |
| of which reasoning | 0 | 720 |
| tool calls | 5.1 | 7.9 |
| cache hit rate | 84% | 83% |

Command Code had reasoning turned on by default; DeepInfra did not. With identical client settings, the
Command Code runs produced about twice the output, made more tool calls, and carried bigger contexts. That
is why Command Code used 2.5× the credit per task. Its per-token rates are about the same as DeepInfra's promo
for cached input, 1.5× for fresh input and 2× for output, so most of the gap comes from the extra tokens, not the rates. Reasoning didn't change the outcome: both passed everything. On harder work it might.

### Speed

| | DeepInfra | Command Code |
|---|---|---|
| median time to first token | 0.70 s | 1.37 s |
| median time to response headers | 0.34 s | 1.36 s |
| median output speed | 232 tok/s | 280 tok/s |
| median wall time per task | 55 s | 72 s |

Command Code took about a second longer to start each response (headers at 1.36 s vs 0.34 s), which adds
up over ~7 requests per task. Once it started, it generated faster. Combined with the extra reasoning, a
task took about 30% longer.

### Reliability

No malformed tool calls, rate limits, caps, timeouts or errors on either side across 538 requests.
Command Code advertises server-side tool-call repair, but with zero malformed calls on DeepInfra too, this run
couldn't show whether it helps.

## Caveats

- **The tasks were too easy to separate quality.** 40/40 on both sides means this run measured price and
  speed, not capability. A 95% confidence interval on 40/40 still runs down to 91%. Harder, longer tasks
  are the obvious follow-up.
- **Small tasks.** About 50–60k prompt tokens per task, mostly cached. Real sessions on a large codebase
  can be 10–50× bigger. The cost per task scales with session size, but the break-even in dollars doesn't change.
- **The Command Code cost is an estimate** from token counts at their published rates; the API doesn't
  return a cost. DeepInfra's is the cost it reported per request. Two runs interrupted by a restart
  (well under 1¢) are not counted.
- **Promos on both sides.** DeepInfra's 51% discount and Command Code's boosted $100 DeepSeek allowance
  can end at any time. Without the DeepInfra promo, its cost per task roughly doubles.
- **Reasoning defaults differed.** The two routes weren't configured identically at the server end. That's
  part of what you get from each, but it means "same model" doesn't mean same behaviour.
- **One evening, off-peak.** About half the runs had 2 agents running at once and the rest had 4. Both
  sides always ran under the same load.

## Bottom line

If you run a coding agent all day, every day, the $10 plan buys roughly 4× more work per dollar than
pay-as-you-go, and its caps won't get in your way on a cheap model. If you use an agent a few times a day,
$10 of API credit goes further: it lasts for months, responds faster, and you're not paying for an
allowance you don't use. Command Code also turns on reasoning by default, which costs credit and time;
whether that's worth it depends on how hard your tasks are.

*Method, tasks, harness and raw logs: [[link to repo]].*
