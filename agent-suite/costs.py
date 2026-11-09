"""Shared cost / cap accounting for proxy log records. Used by run_suite.py and analyze.py.

Three ways to put a dollar figure on a request:

- list value   tokens x `list_price` (DeepSeek's official rates, identical on every side).
               The neutral yardstick: "how much model usage did this side deliver".
- billed       what this side actually charged for it, per the side's `billing`:
                 {"basis": "reported_cost"}   provider-reported cost (OpenRouter `usage.cost`);
                                              falls back to tokens x `fallback_price` if absent
                 {"basis": "credits"}         plan credits: tokens x `rate` (default: list_price),
                                              x `peak.multiplier` during the plan's peak hours
                 {"basis": "list_value"}      same as list value
- plan dollars (subscriptions only) billed credits converted to the share of the plan price used:
               credits x plan.price_usd / plan.monthly_credits_usd
"""
import re
from datetime import datetime, timedelta


def tokens(r):
    pt = r.get("prompt_tokens") or 0
    cached = r.get("cached_tokens") or 0
    return max(pt - cached, 0), cached, r.get("completion_tokens") or 0


def price_tokens(r, price):
    uncached, cached, out = tokens(r)
    return (uncached * price["input"] + cached * price.get("cached_input", price["input"])
            + out * price["output"]) / 1e6


def parse_ts(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def is_peak(ts, peak):
    """peak = {"utc_hours": [...], "weekdays": [0..6, Mon=0], "multiplier": 2}"""
    if not peak or not ts:
        return False
    t = parse_ts(ts)
    return t.weekday() in peak.get("weekdays", range(7)) and t.hour in peak.get("utc_hours", [])


def list_value(r, side):
    return price_tokens(r, side["list_price"])


def billed(r, side):
    """Dollars (or plan credits) this side charged for one successful request."""
    b = side.get("billing") or {"basis": "list_value"}
    basis = b.get("basis", "list_value")
    if basis == "reported_cost":
        if r.get("reported_cost") is not None:
            return float(r["reported_cost"])
        return price_tokens(r, b.get("fallback_price") or side["list_price"])
    if basis == "credits":
        v = price_tokens(r, b.get("rate") or side["list_price"])
        if is_peak(r.get("ts"), b.get("peak")):
            v *= b["peak"].get("multiplier", 1)
        return v
    return list_value(r, side)


def ok(r):
    return r.get("status") == 200 and not r.get("error")


def counts(r):
    """Did this request consume usage? Successful requests, plus streamed ones that errored after
    usage was reported."""
    return r.get("status") == 200 and r.get("prompt_tokens") is not None


def side_spend(records, side):
    """Billed total for one side over a list of proxy records."""
    return sum(billed(r, side) for r in records if r.get("side") == side["name"] and counts(r))


def classify_error(status, text, side):
    """Return 'cap' (plan/credit limit: stop or wait), 'rate_limit' (transient), or 'error'."""
    rules = side.get("cap_detection") or {}
    text = text or ""
    if status in rules.get("cap_statuses", [402]):
        return "cap"
    pat = rules.get("cap_pattern")
    if pat and status != 200 and re.search(pat, text, re.I):
        return "cap"
    if pat and status == 200 and re.search(pat, text, re.I):  # error delivered inside an SSE stream
        return "cap"
    if status == 429 or re.search(r"rate.?limit", text, re.I):
        return "rate_limit"
    return "error"


_RESET = re.compile(r"resets?\s+in\s+(?:(\d+)\s*d(?:ays?)?)?\s*(?:(\d+)\s*h(?:ours?)?)?\s*(?:(\d+)\s*m(?:in(?:utes?)?)?)?", re.I)


def reset_seconds(msg):
    """Parse 'Resets in 2h 41m' / 'resets in 3 days' style hints; None if absent."""
    m = _RESET.search(msg or "")
    if not m or not any(m.groups()):
        return None
    d, h, mi = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60


def windows(records, side, hours):
    """Replay a plan's rolling window (opens on first request, resets `hours` later) over the side's
    requests. Returns a list of dicts: start, end, billed, list_value, requests, capped_at."""
    out, cur = [], None
    recs = sorted((r for r in records if r.get("side") == side["name"] and r.get("ts")), key=lambda r: r["ts"])
    for r in recs:
        t = parse_ts(r["ts"])
        if cur is None or t >= cur["_end"]:
            cur = {"start": r["ts"], "_end": t + timedelta(hours=hours), "billed": 0.0, "list_value": 0.0,
                   "requests": 0, "capped_at": None}
            out.append(cur)
        cur["requests"] += 1
        if counts(r):
            cur["billed"] += billed(r, side)
            cur["list_value"] += list_value(r, side)
        if r.get("cap") and cur["capped_at"] is None:
            cur["capped_at"] = r["ts"]
    for w in out:
        w["end"] = w.pop("_end").isoformat()
        w["billed"], w["list_value"] = round(w["billed"], 4), round(w["list_value"], 4)
    return out
