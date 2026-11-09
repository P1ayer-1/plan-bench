"""Scripted fake LLM for testing the pipeline offline (no API keys, no spend).

turn 1 -> call the harness's shell tool to copy the task's reference solution; turn 2 -> 'Done.'

  python dev/mock_llm.py [CAP_AFTER] [CAP_FOR_S] [PORT]

Paths starting with /or behave like a pay-as-you-go API (usage.cost + provider in the stream; request #3
gets a transient 429 "Rate limit exceeded"). Paths starting with /cc behave like a Command Code
plan: after CAP_AFTER requests every request gets a 429 "You've reached your 5-hour usage limit
... Resets in 0h 1m" for CAP_FOR_S seconds, then the window resets. Use with dev/mock_config.json.
"""
import json, sys, threading, time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SUITE = Path(__file__).resolve().parent.parent
TASKS = {(SUITE / "tasks" / t.name / "task.md").read_text(encoding="utf-8").splitlines()[0]: t.name
         for t in (SUITE / "tasks").iterdir() if t.is_dir()}
CAP_AFTER = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
CAP_FOR = float(sys.argv[2]) if len(sys.argv) > 2 else 60
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 9100
N = {"cc": 0, "or": 0, "cc_window": 0}
CAPPED_UNTIL = {"t": 0.0}
LOCK = threading.Lock()
LOG = open(Path(__file__).with_name("mock_requests.log"), "a", encoding="utf-8")


def sse(w, obj):
    w.write(f"data: {json.dumps(obj)}\n\n".encode()); w.flush()


def err(h, code, msg):
    h.send_response(code); h.send_header("Content-Type", "application/json"); h.end_headers()
    h.wfile.write(json.dumps({"error": {"message": msg, "code": code}}).encode())


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *a):
        pass

    def do_GET(self):
        b = json.dumps({"data": [{"id": "m"}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        msgs = body.get("messages", []); tools = body.get("tools") or []
        LOG.write(json.dumps({"path": self.path, "n_msgs": len(msgs), "tools": [t["function"]["name"] for t in tools],
                              "auth": self.headers.get("Authorization"), "stream": body.get("stream"),
                              "extra": {k: body[k] for k in ("provider", "usage", "stream_options") if k in body},
                              "first_user": next((str(m.get("content"))[:160] for m in msgs if m.get("role") == "user"), None)}) + "\n")
        LOG.flush()
        is_cc = self.path.startswith("/cc")
        with LOCK:
            if is_cc:
                now = time.time()
                if CAPPED_UNTIL["t"] and now >= CAPPED_UNTIL["t"]:  # window reset
                    CAPPED_UNTIL["t"], N["cc_window"] = 0.0, 0
                if CAPPED_UNTIL["t"]:
                    return err(self, 429, "You've reached your 5-hour usage limit for your plan. Resets in 0h 1m.")
                N["cc"] += 1; N["cc_window"] += 1
                if N["cc_window"] > CAP_AFTER:
                    CAPPED_UNTIL["t"] = now + CAP_FOR
                    return err(self, 429, "You've reached your 5-hour usage limit for your plan. Resets in 0h 1m.")
            else:
                N["or"] += 1
                if N["or"] == 3:
                    return err(self, 429, "Rate limit exceeded: upstream provider is busy, retry shortly")

        def text_of(m):
            c = m.get("content")
            return c if isinstance(c, str) else " ".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
        text_all = " ".join(text_of(m) for m in msgs)
        task = next((v for k, v in TASKS.items() if k[:60] in text_all), None)
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.end_headers()
        base = {"id": "x", "object": "chat.completion.chunk", "created": int(time.time()), "model": body.get("model")}
        if not is_cc:
            base["provider"] = "DeepInfra"
        usage = {"prompt_tokens": 9000, "completion_tokens": 150, "total_tokens": 9150,
                 "prompt_tokens_details": {"cached_tokens": 8000}}
        if not is_cc:
            usage["cost"] = (1000 * 0.098 + 8000 * 0.00294 + 150 * 0.294) / 1e6
        did_tool = any(m.get("role") == "tool" for m in msgs)
        shell = next((t for t in tools if t["function"]["name"] in ("bash", "shell")), None)
        if tools and shell and task and not did_tool:
            params = shell["function"].get("parameters", {}).get("properties", {})
            src = (SUITE / "validation" / "refs" / task).as_posix()
            args = {"command": f"cp -r '{src}/.' ."}
            if "description" in params:
                args["description"] = "apply fix"
            a = json.dumps(args)
            sse(self.wfile, {**base, "choices": [{"index": 0, "delta": {"role": "assistant", "tool_calls": [
                {"index": 0, "id": "call_1", "type": "function", "function": {"name": shell["function"]["name"], "arguments": ""}}]}}]})
            for i in range(0, len(a), 15):
                sse(self.wfile, {**base, "choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": a[i:i + 15]}}]}}]})
            sse(self.wfile, {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]})
        else:
            sse(self.wfile, {**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": "Done."}}]})
            sse(self.wfile, {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
        sse(self.wfile, {**base, "choices": [], "usage": usage})
        self.wfile.write(b"data: [DONE]\n\n"); self.wfile.flush()


print(f"mock LLM on 127.0.0.1:{PORT}  cc caps after {CAP_AFTER} req/window for {CAP_FOR}s", flush=True)
ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
