#!/usr/bin/env python3
"""
Logging proxy for agent benchmarks.

Sits between your agent harness (opencode, Pi, etc.) and each upstream API.
Route by path prefix:  http://127.0.0.1:8899/<side>/v1/chat/completions
                   or:  http://127.0.0.1:8899/<side>/run/<run_id>/v1/chat/completions
  -> forwards to that side's base_url, injecting the real API key. The second form tags every
     request with its run (run_suite.py uses it, so concurrent runs are attributed correctly).

Logs one JSON line per request to proxy_log.jsonl with: run tag (side/task/repeat),
status, tokens (prompt / cached / completion / reasoning), OpenRouter-reported cost,
latency, time-to-first-token, tool-call count, malformed tool-call count, the model/provider the
upstream says served it, and errors classified per side as `cap` (plan or credit limit) vs
`rate_limit` (transient) vs `error` -- see `cap_detection` in suite_config.json and costs.py.

Control endpoints:
  POST /_tag  {"run_id": "...", "task": "...", "repeat": 1}   -> tags later untagged requests (legacy)
  GET  /_health

Usage:
  python proxy.py --config suite_config.json
"""
import argparse, json, os, sys, threading, time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from config import load_config
from costs import classify_error

ROOT = Path(__file__).parent

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

LOCK = threading.Lock()
STATE = {"tag": {}}
HOP = {"host", "content-length", "connection", "transfer-encoding", "accept-encoding", "authorization"}


def log(path, rec):
    with LOCK, open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


class StreamStats:
    """Parse SSE chat-completion chunks as they pass through."""
    def __init__(self, t0=None):
        self.buf = b""
        self.usage = None
        self.ttft = None
        self.tool_args = {}  # index -> accumulated argument string
        self.error = None
        self.served_model = None
        self.provider = None
        self.finish_reason = None
        self.t0 = t0 if t0 is not None else time.monotonic()  # request start, not header arrival: some upstreams send headers only after generating

    def feed(self, data: bytes):
        self.buf += data
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            line = line.strip()
            if not line.startswith(b"data:"):
                continue
            payload = line[5:].strip()
            if payload == b"[DONE]":
                continue
            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if chunk.get("error"):
                self.error = json.dumps(chunk["error"])[:500]
            self.served_model = chunk.get("model") or self.served_model
            self.provider = chunk.get("provider") or self.provider
            for ch in chunk.get("choices") or []:
                self.finish_reason = ch.get("finish_reason") or self.finish_reason
                d = ch.get("delta") or {}
                if self.ttft is None and (d.get("content") or d.get("reasoning")
                                          or d.get("reasoning_content") or d.get("tool_calls")):
                    self.ttft = time.monotonic() - self.t0
                for tc in d.get("tool_calls") or []:
                    i = tc.get("index", 0)
                    fn = tc.get("function") or {}
                    self.tool_args.setdefault(i, "")
                    self.tool_args[i] += fn.get("arguments") or ""
            if chunk.get("usage"):
                self.usage = chunk["usage"]

    def tool_summary(self):
        bad = 0
        for s in self.tool_args.values():
            try:
                json.loads(s or "{}")
            except json.JSONDecodeError:
                bad += 1
        return len(self.tool_args), bad


def tool_summary_nonstream(resp):
    n = bad = 0
    for ch in resp.get("choices") or []:
        for tc in (ch.get("message") or {}).get("tool_calls") or []:
            n += 1
            try:
                json.loads((tc.get("function") or {}).get("arguments") or "{}")
            except json.JSONDecodeError:
                bad += 1
    return n, bad


def make_handler(cfg):
    sides = {s["name"]: s for s in cfg["sides"]}
    log_path = ROOT / cfg.get("proxy_log", "results/proxy_log.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"  # close after each response; keeps streaming simple

        def log_message(self, *a):
            pass

        def _json(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _route(self):
            """-> (side, upstream_url, tag)"""
            parts = self.path.lstrip("/").split("/", 1)
            side = sides.get(parts[0])
            if not side:
                return None, None, None
            rest = parts[1] if len(parts) > 1 else ""
            tag = STATE["tag"]
            if rest.startswith("run/"):
                _, run_id, rest = (rest.split("/", 2) + ["", ""])[:3]
                bits = run_id.split("--")  # <side>--<task>--r<repeat>--<stamp>
                tag = {"run_id": run_id, "task": bits[1] if len(bits) > 1 else None,
                       "repeat": int(bits[2][1:]) if len(bits) > 2 and bits[2][1:].isdigit() else None}
            if rest.startswith("v1/"):
                rest = rest[3:]
            return side, side["base_url"].rstrip("/") + "/" + rest, tag

        def do_GET(self):
            if self.path == "/_health":
                return self._json(200, {"ok": True, "tag": STATE["tag"]})
            side, url, _ = self._route()
            if not side:
                return self._json(404, {"error": "unknown side"})
            try:
                r = requests.get(url, headers=self._headers(side), timeout=60)
            except Exception as e:
                return self._json(502, {"error": {"message": f"proxy upstream error: {e}"}})
            self.send_response(r.status_code)
            self.send_header("Content-Type", r.headers.get("Content-Type", "application/json"))
            self.end_headers()
            self.wfile.write(r.content)

        def _headers(self, side):
            h = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
            h["Authorization"] = "Bearer " + os.environ[side["api_key_env"]]
            h.update(side.get("extra_headers", {}))
            return h

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b""
            if self.path == "/_tag":
                STATE["tag"] = json.loads(raw or b"{}")
                return self._json(200, {"ok": True})

            side, url, tag = self._route()
            if not side:
                return self._json(404, {"error": "unknown side"})
            try:
                body = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                body = None

            stream = bool(body and body.get("stream"))
            if body is not None:
                if stream:
                    body.setdefault("stream_options", {})["include_usage"] = True
                for k, v in side.get("inject_body", {}).items():
                    body.setdefault(k, v)
                raw = json.dumps(body).encode()

            rec = {"ts": datetime.now(timezone.utc).isoformat(), "side": side["name"],
                   **tag, "path": self.path, "model": (body or {}).get("model"),
                   "stream": stream, "n_messages": len((body or {}).get("messages") or [])}
            t0 = time.monotonic()
            try:
                r = requests.post(url, headers={**self._headers(side), "Content-Type": "application/json"},
                                  data=raw, stream=True, timeout=cfg.get("upstream_timeout_s", 900))
            except Exception as e:
                rec.update(status=-1, error=repr(e)[:500], latency_s=round(time.monotonic() - t0, 2))
                log(log_path, rec)
                return self._json(502, {"error": {"message": f"proxy upstream error: {e}"}})

            rec["status"] = r.status_code
            rec["headers_s"] = round(time.monotonic() - t0, 3)  # time until response headers arrived
            self.send_response(r.status_code)
            self.send_header("Content-Type", r.headers.get("Content-Type", "application/json"))
            self.end_headers()

            if r.status_code == 200 and stream:
                st = StreamStats(t0)
                try:
                    for chunk in r.iter_content(chunk_size=None):
                        if chunk:
                            st.feed(chunk)
                            self.wfile.write(chunk)
                            self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    rec["client_disconnected"] = True
                usage, (ntc, bad) = st.usage or {}, st.tool_summary()
                rec["ttft_s"] = round(st.ttft, 3) if st.ttft is not None else None
                rec.update(served_model=st.served_model, provider=st.provider, finish_reason=st.finish_reason)
                if st.error:
                    rec["error"] = st.error
            else:
                content = r.content
                try:
                    self.wfile.write(content)
                except (BrokenPipeError, ConnectionResetError):
                    rec["client_disconnected"] = True
                usage, ntc, bad = {}, 0, 0
                if r.status_code == 200:
                    try:
                        j = json.loads(content)
                        usage = j.get("usage") or {}
                        ntc, bad = tool_summary_nonstream(j)
                        rec.update(served_model=j.get("model"), provider=j.get("provider"))
                    except json.JSONDecodeError:
                        pass
                else:
                    rec["error"] = content[:500].decode(errors="replace")

            rec.update(
                latency_s=round(time.monotonic() - t0, 3),
                prompt_tokens=usage.get("prompt_tokens"),
                cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                reported_cost=usage.get("cost", usage.get("estimated_cost")),  # OpenRouter: cost; DeepInfra: estimated_cost
                tool_calls=ntc, malformed_tool_calls=bad,
            )
            kind = classify_error(r.status_code, rec.get("error"), side) if rec.get("error") or r.status_code != 200 else None
            rec.update(error_kind=kind, cap=kind == "cap", rate_limited=kind == "rate_limit")
            log(log_path, rec)

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="suite_config.json")
    a = ap.parse_args()
    cfg = load_config(a.config)
    for s in cfg["sides"]:
        if not os.environ.get(s["api_key_env"]):
            sys.exit(f"Missing env var {s['api_key_env']} for side {s['name']}")
    host, port = cfg.get("proxy_host", "127.0.0.1"), cfg.get("proxy_port", 8899)
    print(f"proxy on http://{host}:{port}  sides: {', '.join(s['name'] for s in cfg['sides'])}")
    ThreadingHTTPServer((host, port), make_handler(cfg)).serve_forever()


if __name__ == "__main__":
    main()
