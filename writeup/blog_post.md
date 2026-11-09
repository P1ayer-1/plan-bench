# $10 of API credits vs a $10/month coding plan: what each buys for agentic coding

*Measured November 8–9, 2026. Prices and promos change; check them before relying on these numbers.
Method, tasks, harness and raw logs: https://github.com/P1ayer-1/plan-bench.*

**TL;DR:** Same model (DeepSeek V4.1 Flash), same coding agent, same 13 tasks, through two routes: DeepInfra's
pay-as-you-go API, and Command Code's $10/month GOAT plan. Each route ran with reasoning on and off.

- **Whether reasoning is on decided quality; the route didn't.** With reasoning on, both routes passed every hard task
  (25/25 each). With it off, they passed 19/25 and 21/25. With reasoning matched, the two routes were indistinguishable.
- **Reasoning also made the API route cheaper.** Without it, the agent took nearly twice as many turns and
  sometimes timed out. With reasoning on, DeepInfra cost **$0.0028 per passed task**, so $10 covers about 3,500 tasks.
- **The plan buys more, if you use it.** Command Code used $0.0083 of plan credit per passed task, which
  works out to roughly 12,000 tasks a month for $10. Its peak-hour pricing (2×) applied to over half
  the run. Off-peak, the same work would be about 19,000 tasks.
- **Break-even is about 120 passed agent tasks a day.** Below that, $10 of API credit costs less and lasts longer than
  a month. Neither route hit a cap, a rate limit, or a malformed tool call in 2,863 requests.

## The question

Command Code's GOAT plan costs $10 a month and advertises up to $100 of DeepSeek V4.1 Flash usage. The alternative
is to put $10 straight onto an inference provider and pay per token. "10× the value" only counts if you can use it,
and "same model" only means something if both routes behave the same. So I measured what each route delivers for
agentic coding: tasks passed, cost per passed task, speed, reliability, and whether the plan's limits kick in.

## Setup

**Routes.**

- **DeepInfra**, direct API, serving the Oct 17 snapshot (`deepseek-ai/DeepSeek-V4.1-Flash-1017`). It had a 51% promo:
  $0.098 / $0.294 / $0.00294 per million tokens (input / output / cached input), down from $0.20 / $0.60 / $0.006.
  OpenRouter routed to DeepInfra charges the same per token, plus a fee when you buy credits, so direct is the
  cheapest way to spend $10 on this model via API.
- **Command Code GOAT**, $10/month: up to $100 of DeepSeek V4.1 Flash usage a month, at most $20 per 5 hours and $50
  per 7 days. Usage is charged at $0.15 / $0.60 / $0.003 per million tokens, **doubled in weekday peak hours**
  (01–04 and 06–10 UTC). It serves `deepseek/deepseek-v4.1-flash` ("latest") and reports no snapshot date, so I
  couldn't confirm it's the same weights.

**Reasoning.** The routes don't share defaults: Command Code reasons by default; DeepInfra doesn't. Both accept a
`reasoning_effort` parameter, so each route ran both ways: DeepInfra off (default) and `medium`; Command Code on
(default) and `off`. That gives four sides.

**Agent and harness.** opencode 1.19.5, run unattended in a Docker container with identical configuration
on every side. A logging proxy between the agent and each API recorded every request: tokens, cache hits,
latency, tool calls, errors, and caps vs rate limits.

**Tasks.** 13 tasks on a small Python personal-finance library, each graded by hidden tests the agent never sees.

- **8 core tasks:** a feature, two bug fixes, a refactor, writing tests (graded by catching planted bugs), a
  multi-file change, an exact-output CLI command, and a performance fix.
- **5 hard tasks:** recurring transactions with month-end and leap-year rules, a search-query language with
  precedence and quoting, bank reconciliation that needs an optimal matching (greedy fails the tests), historical
  exchange rates with inverse and cross rates and round-once arithmetic, and budget rollover with caps and refunds.

**Procedure.** 5 rounds of all 13 tasks on all four sides: 260 runs, with up to 6 agents at once. The sides ran in
lockstep, so they shared load and time of day. 00:15–02:08 UTC on Monday, Nov 9, so over half of each Command Code
side's requests fell in peak hours. A smaller pilot the evening before (2 sides × 8 core tasks × 5 rounds,
off-peak) agrees with these results.

## Results

### Quality: reasoning matters, the route doesn't

| passed | DeepInfra, off | DeepInfra, on | Command Code, on | Command Code, off |
|---|---|---|---|---|
| core (40 runs each) | 40 | 40 | 39 | 39 |
| hard (25 runs each) | **19** | **25** | **25** | **21** |
| total (95% CI) | 91% [81–96] | 100% [94–100] | 98% [92–100] | 92% [83–97] |

Paired on the same task and round:

- **DeepInfra off vs on:** the 6 disagreements all favour reasoning (sign test p = 0.03).
- **Reasoning on, DeepInfra vs Command Code:** 64 both passed, 1 disagreement.
- **Reasoning off, DeepInfra vs Command Code:** 5 vs 6 disagreements, no difference.

With reasoning matched, I found no quality difference between the routes. Without reasoning, the model
failed hard tasks on both routes, and DeepInfra's no-reasoning agent hit the 20-minute limit 4 times (3 on t11
reconciliation, 1 on t12 exchange rates), looping through up to 185 requests. Two of those runs still
left passing code behind.

### Cost: what $10 buys

| | DeepInfra, off | DeepInfra, on | Command Code, on | Command Code, off |
|---|---|---|---|---|
| charged per graded run (95% CI) | $0.0034 [0.0020–0.0052] | $0.0028 [0.0024–0.0033] | $0.0082 credit [0.0065–0.0101] | $0.0055 credit [0.0044–0.0068] |
| charged per passed task | $0.0037 | $0.0028 | $0.0083 credit | $0.0060 credit |
| passed tasks per $10 | ~2,700 | ~3,500 | ~12,000 / month* | ~16,800 / month* |

\*If you use the whole $100 monthly allowance, at this run's mix of peak and off-peak pricing.

**Reasoning was cheaper on DeepInfra.** That sounds backwards until you look at the sessions: without reasoning,
the agent averaged 16.9 requests and 387k prompt tokens per run, against 9.5 requests and 113k with reasoning. Cheap
thinking beat expensive flailing. On Command Code the opposite held ($0.0083 vs $0.0060 per passed task), but there
reasoning bought 4 extra hard-task passes.

**Matched on reasoning, the routes used about the same tokens.** At DeepSeek's list price, a passed task
consumed $0.0050 of tokens on DeepInfra and $0.0053 on Command Code. The cost gap is all pricing:

- DeepInfra's promo charges about 0.56× list price.
- Command Code charges 1× list price off-peak and 2× at peak, but gives you $100 of credit for $10.
- 56% of the Command Code requests were at peak, so this run paid about 1.6× list price there.

**Break-even.** With reasoning on, $10/month of plan buys about 12,000 passed tasks a month if fully used, against
about 3,500 per $10 on DeepInfra. The plan wins once you'd spend more than $10 a month on DeepInfra: about **3,500
passed tasks a month, or roughly 120 a day**. Below that, the $10 of API credit is cheaper, and it isn't gone at
the end of the month. These tasks averaged about 100k prompt tokens per run (mostly cached); bigger real-world
sessions cost proportionally more, which lowers the break-even task count but not the dollar logic.

### The caps don't bind

Both Command Code sides draw on the same plan, and together they used about $0.89 of credit, against a $20 five-hour
window, while sharing 6 agents for nearly two hours. The plan's rolling windows are irrelevant for one developer on a model this cheap. What binds is
the $100 monthly allowance (the $50 weekly cap means at least two weeks of heavy use to exhaust it) and
time of day: peak hours (01–04 and 06–10 UTC on weekdays) cover a US evening and an Asian morning, and every
request there costs double.

### Speed

| median | DeepInfra, off | DeepInfra, on | Command Code, on | Command Code, off |
|---|---|---|---|---|
| time to response headers | 0.44 s | 0.38 s | 1.40 s | 1.39 s |
| time to first token | 0.79 s | 0.72 s | 1.41 s | 1.41 s |
| output speed | 226 tok/s | 186 tok/s | 234 tok/s | 291 tok/s |
| wall time per task | 66 s | 94 s | 86 s | 71 s |

Command Code adds about a second before each response starts (headers at ~1.4 s vs ~0.4 s), then streams
faster. Over a whole task that roughly evens out; with reasoning on, Command Code finished tasks slightly faster.

### Reliability

Across 2,863 requests: no malformed tool calls, rate limits, caps or API errors on any side. The only failures
were the agent's own: wrong answers on hard tasks, plus 4 timeouts by the no-reasoning DeepInfra agent on t11.

## Caveats

- **The Command Code cost is computed, then checked.** The API returns no cost, so I priced each request from
  its token counts at the published rates, including the peak multiplier. Studio's usage history only goes back
  100 requests, but all 100 it showed (all at peak) matched my figure exactly, to the request. Pricing them at
  off-peak rates would have given exactly half. Studio's totals (1,485 requests, 15.8M tokens, about 1% of the
  monthly allowance) also match the proxy log.
- **Snapshot.** Command Code's "latest" may not be the exact 1017 weights. Quality was indistinguishable once
  reasoning was matched.
- **Promos on both sides.** Without DeepInfra's 51% discount, its cost per task roughly doubles and the break-even
  halves. Command Code's $100 DeepSeek allowance is also a "boosted" deal.
- **Sample size.** 65 runs per side; the hard-task differences are 4–6 runs out of 25. The reasoning effect is
  consistent across both routes and significant on DeepInfra; differences between routes aren't.
- **Task size.** Small to medium sessions on a small library. Very large codebases and long sessions change the
  absolute numbers.
- **One harness.** Agents other than opencode may set reasoning or caching differently.

## Bottom line

- **Turn reasoning on.** On DeepSeek V4.1 Flash it was the difference between 76–84% and 100% on hard tasks,
  and on the pay-as-you-go route it was cheaper too.
- **The route doesn't change quality.** Same model, same answers. What differs is price, latency, and defaults.
- **Light to moderate use (under ~120 agent tasks a day): $10 of API credit.** It's cheaper, starts each
  response a second sooner, and doesn't expire at the end of the month.
- **Heavy daily use: the $10 plan,** worth roughly 3–5× as many tasks per dollar, more if you work outside
  01–04 and 06–10 UTC on weekdays. The caps won't get in your way on a model this cheap.
