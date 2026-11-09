#!/usr/bin/env python3
"""
Drive an agent harness (opencode by default) through every task, on every side,
in fresh copies of the sandbox repo. Traffic goes through proxy.py, which logs
tokens/caching/latency/tool-call health per request; this script grades results.

  1. python preflight.py --config suite_config.json     (once: keys, served model, caching, cost field)
  2. python proxy.py --config suite_config.json         (separate terminal)
  3. python run_suite.py --config suite_config.json
  4. python analyze.py --config suite_config.json

Scheduling: every side walks the same (round, task) sequence. The next job always goes to the
awake side that has started the fewest jobs (ties alternate), so sides stay in lockstep and
time-of-day load hits them equally. A side stops when it reaches its `budget_usd` (in its own
billing basis, see costs.py), finishes the sequence, or hits a cap it is not set to wait out.
A side that is set to wait sleeps until the reset time named in the cap message, then re-runs
the job that was cut off, while the other sides keep going.

`--until-exhausted` (or "repeats": "until_exhausted") cycles the task list up to `max_repeats`
rounds. `--workers N` runs N agents at once (each run is tagged by URL, so the proxy log stays
correctly attributed); use it to push a subscription into its rolling window cap.
"""
import argparse, copy, json, os, shutil, signal, subprocess, sys, threading, time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import requests
from config import load_config
from costs import reset_seconds, side_spend
from grading import grade

ROOT = Path(__file__).parent
WRITE_LOCK = threading.Lock()


def fill(obj, **kw):
    """Recursively substitute {placeholders} in strings, dict keys included."""
    if isinstance(obj, str):
        for k, v in kw.items():
            obj = obj.replace("{" + k + "}", str(v))
        return obj
    if isinstance(obj, list):
        return [fill(x, **kw) for x in obj]
    if isinstance(obj, dict):
        return {fill(k, **kw): fill(v, **kw) for k, v in obj.items()}
    return obj


def load_proxy_log(cfg):
    p = ROOT / cfg["proxy_log"]
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def git(ws, *args, **kw):
    return subprocess.run(["git", "-c", "safe.directory=*", "-c", "core.autocrlf=false", "-c", "core.safecrlf=false", *args],
                          cwd=ws, **kw)


def resolve_exe(name):
    """Find the harness binary. On Windows, npm installs a .cmd shim, and anything run through
    cmd.exe has its double quotes stripped from arguments -- which silently corrupts task prompts
    like `Money("10.00")`. So follow the shim to the real .exe it launches."""
    exe = shutil.which(name)
    if exe and os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        import re
        m = re.search(r'"%dp0%\\([^"]+?\.exe)"', Path(exe).read_text(errors="replace"))
        target = (Path(exe).parent / m.group(1)).resolve() if m else None
        if not target or not target.exists():
            sys.exit(f"{exe} is a cmd.exe shim and its .exe target could not be found; prompts would be "
                     f"mangled. Put the real executable on PATH or set agent.cmd[0] to its full path.")
        exe = str(target)
    return exe


def run_agent(cmd, ws, env, timeout, so, se, stdin=None):
    """Run the harness; on timeout kill the whole process tree (the harness spawns shells/LSPs)."""
    exe = resolve_exe(cmd[0])
    if not exe:
        sys.exit(f"agent command not found: {cmd[0]}")
    kw = {"start_new_session": True} if os.name != "nt" else \
         {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    p = subprocess.Popen([exe, *cmd[1:]], cwd=ws, stdout=so, stderr=se, stdin=stdin or subprocess.DEVNULL, env=env, **kw)
    try:
        return p.wait(timeout=timeout), False
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
        else:
            os.killpg(p.pid, signal.SIGKILL)
        p.wait()
        return None, True


def run_one(cfg, side, task, rep, results_path):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    run_id = f"{side['name']}--{task.name}--r{rep}--{stamp}"
    run_dir = ROOT / cfg["results_dir"] / "runs" / run_id
    ws = run_dir / "ws"
    shutil.copytree(ROOT / "sandbox", ws, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    git(ws, "init", "-q")
    git(ws, "add", "-A")
    git(ws, "-c", "user.email=b@b", "-c", "user.name=bench", "commit", "-qm", "base")

    proxy = f"http://{cfg['proxy_host']}:{cfg['proxy_port']}"
    agent = cfg["agent"]
    kw = dict(workspace=ws, model=side["model"], proxy_url=f"{proxy}/{side['name']}/run/{run_id}/v1",
              prompt=(task / "task.md").read_text(encoding="utf-8") + agent.get("prompt_suffix", ""))
    if agent.get("config_file"):
        (ws / agent["config_file"]).write_text(json.dumps(fill(copy.deepcopy(agent["config"]), **kw), indent=2),
                                               encoding="utf-8")
        # keep the harness config out of the agent's diff
        with open(ws / ".git" / "info" / "exclude", "a", encoding="utf-8") as f:
            f.write(agent["config_file"] + "\n")
    cmd = fill(agent["cmd"], **kw)
    # The prompt goes in on stdin unless the command line asks for {prompt}: passing a multi-line
    # prompt with quotes through argv is lossy on Windows (opencode.exe receives it re-escaped).
    prompt_file = run_dir / "prompt.txt"
    prompt_file.write_text(kw["prompt"], encoding="utf-8", newline="\n")
    use_stdin = not any("{prompt}" in c for c in agent["cmd"])

    env = dict(os.environ)
    for k in [k for k in env if k.endswith("_API_KEY")]:  # the agent only ever talks to the proxy
        env.pop(k)
    if agent.get("isolate_home"):  # don't let the user's global harness config leak into runs
        shared = ROOT / cfg["results_dir"] / "xdg"  # empty config + package cache, shared so runs don't re-download
        env["XDG_CONFIG_HOME"], env["XDG_CACHE_HOME"] = str(shared / "config"), str(shared / "cache")
        for k in ("XDG_STATE_HOME", "XDG_DATA_HOME"):  # sessions/history: per run, so concurrent runs can't collide
            env[k] = str(run_dir / "xdg" / k.lower())
    env.update(agent.get("env", {}))

    started = datetime.now(timezone.utc).isoformat()
    t0 = time.monotonic()
    with open(run_dir / "agent_stdout.txt", "w", encoding="utf-8") as so, \
         open(run_dir / "agent_stderr.txt", "w", encoding="utf-8") as se, \
         open(prompt_file, "rb") as pin:
        code, timed_out = run_agent(cmd, ws, env, cfg["agent_timeout_s"], so, se, pin if use_stdin else None)
    wall = round(time.monotonic() - t0, 1)

    if agent.get("config_file"):
        (ws / agent["config_file"]).unlink(missing_ok=True)
    diff = git(ws, "diff", "--stat", capture_output=True, text=True, encoding="utf-8").stdout or ""
    git(ws, "add", "-A")
    full = git(ws, "diff", "--cached", capture_output=True, text=True, encoding="utf-8").stdout or ""
    (run_dir / "agent.diff").write_text(full, encoding="utf-8")

    g = grade(task, ws)
    recs = [r for r in load_proxy_log(cfg) if r.get("run_id") == run_id]
    caps = [r for r in recs if r.get("cap")]
    row = {"run_id": run_id, "started": started, "ts": datetime.now(timezone.utc).isoformat(),
           "side": side["name"], "task": task.name, "repeat": rep,
           "passed": g["passed"], "visible_passed": g["visible_passed"],
           "agent_exit": code, "agent_timeout": timed_out, "wall_s": wall, "requests": len(recs),
           "capped": bool(caps), "cap_message": (caps[0].get("error") or "")[:300] if caps else None,
           "rate_limited_requests": sum(bool(r.get("rate_limited")) for r in recs),
           "diff_stat": diff.strip().splitlines()[-1] if diff.strip() else ""}
    with WRITE_LOCK, open(results_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    (run_dir / "grade.txt").write_text(g["detail"], encoding="utf-8")
    shutil.rmtree(run_dir / "xdg", ignore_errors=True)
    print(f"  {side['name']:18} {task.name:22} r{rep}  {'PASS' if g['passed'] else 'fail'}  "
          f"{wall:7.1f}s  req={len(recs)}{'  CAPPED' if caps else ''}{'  TIMEOUT' if timed_out else ''}",
          flush=True)
    return row


def cap_wait_seconds(cfg, side, row):
    """How long to wait before retrying a capped side, or None to stop that side."""
    pol = {"wait_on_cap_minutes": cfg.get("wait_on_cap_minutes", 0), "max_single_wait_hours": 6,
           **side.get("cap_policy", {})}
    if not pol["wait_on_cap_minutes"]:
        return None
    hinted = reset_seconds(row.get("cap_message"))
    secs = hinted + pol.get("reset_margin_s", 120) if hinted is not None else pol["wait_on_cap_minutes"] * 60
    if secs > pol["max_single_wait_hours"] * 3600:
        print(f"  {side['name']}: reset is {secs / 3600:.1f}h away (> max_single_wait_hours) — stopping that side")
        return None
    return secs


class Scheduler:
    def __init__(self, cfg, sides, seq):
        self.cfg, self.sides = cfg, sides
        self.cv = threading.Condition()
        self.st = {s["name"]: {"pending": deque(seq), "started": 0, "inflight": 0, "asleep_until": 0.0,
                               "waits": 0, "done": False} for s in sides}
        self.tick = 0

    def _finish(self, name, why, early=False):
        st = self.st[name]
        if not st["done"]:
            st["done"] = True
            st["pending"].clear()
            print(f"  {name}: {why}", flush=True)
            if early and self.cfg.get("stop_together"):
                # Paired comparison: the other sides do exactly as many jobs as this one got, then stop.
                for other, ost in self.st.items():
                    if not ost["done"]:
                        keep = max(st["started"] - ost["started"], 0)
                        while len(ost["pending"]) > keep:
                            ost["pending"].pop()
                        print(f"  {other}: stop_together — {keep} more job(s) to match {name}", flush=True)

    def next_job(self):
        """Block until a job is available; return (side, rep, task) or None when everything is done."""
        with self.cv:
            while True:
                now = time.time()
                for s in self.sides:
                    st = self.st[s["name"]]
                    if not st["done"] and not st["pending"] and not st["inflight"]:
                        self._finish(s["name"], "finished the task sequence")
                if all(st["done"] and not st["inflight"] for st in self.st.values()):
                    self.cv.notify_all()
                    return None
                ready = [s for s in self.sides if not self.st[s["name"]]["done"]
                         and self.st[s["name"]]["pending"] and self.st[s["name"]]["asleep_until"] <= now]
                for s in list(ready):
                    budget = s.get("budget_usd")
                    if budget:
                        spent = side_spend(load_proxy_log(self.cfg), s)
                        if spent >= budget:
                            self._finish(s["name"], f"reached its budget (${spent:.3f} of ${budget}) — stopping", early=True)
                            ready.remove(s)
                if ready:
                    self.tick += 1
                    low = min(self.st[s["name"]]["started"] for s in ready)
                    tied = [s for s in ready if self.st[s["name"]]["started"] == low]
                    side = tied[self.tick % len(tied)]
                    st = self.st[side["name"]]
                    rep, task = st["pending"].popleft()
                    st["started"] += 1
                    st["inflight"] += 1
                    return side, rep, task
                sleepers = [st["asleep_until"] for st in self.st.values() if not st["done"] and st["pending"]]
                timeout = max(min(sleepers) - now, 1) if sleepers else None
                self.cv.wait(timeout=timeout)

    def report(self, side, rep, task, row):
        with self.cv:
            name, st = side["name"], self.st[side["name"]]
            st["inflight"] -= 1
            if row["capped"] and not st["done"]:
                st["pending"].appendleft((rep, task))  # re-run the job the cap cut off
                st["started"] -= 1
                if st["asleep_until"] <= time.time():  # first worker to see this cap decides
                    secs = cap_wait_seconds(self.cfg, side, row)
                    limit = side.get("cap_policy", {}).get("max_cap_waits", 3)
                    if secs is None or (limit is not None and st["waits"] >= limit):
                        self._finish(name, f"hit a usage cap — stopping: {row['cap_message']}", early=True)
                    else:
                        st["waits"] += 1
                        st["asleep_until"] = time.time() + secs
                        print(f"  {name} capped — sleeping {secs / 60:.0f} min (until "
                              f"{datetime.fromtimestamp(st['asleep_until']):%a %H:%M}), then resuming", flush=True)
            self.cv.notify_all()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="suite_config.json")
    ap.add_argument("--tasks", help="comma-separated task names (default: config)")
    ap.add_argument("--repeats", type=int, help="rounds through the task list (max rounds with --until-exhausted)")
    ap.add_argument("--until-exhausted", action="store_true",
                    help="cycle the tasks until every side hits its budget or a cap it won't wait out")
    ap.add_argument("--sides", help="comma-separated side names")
    ap.add_argument("--workers", type=int, default=1, help="agents running at once (default 1)")
    ap.add_argument("--resume", action="store_true",
                    help="skip (side, task, round) jobs that already have a non-capped result in results.jsonl")
    a = ap.parse_args()
    cfg = load_config(a.config)

    try:
        requests.get(f"http://{cfg['proxy_host']}:{cfg['proxy_port']}/_health", timeout=5).raise_for_status()
    except Exception:
        sys.exit("proxy not reachable: start `python proxy.py --config ...` first")
    if not resolve_exe(cfg["agent"]["cmd"][0]):
        sys.exit(f"agent command not found on PATH: {cfg['agent']['cmd'][0]}")

    all_tasks = sorted(p for p in (ROOT / "tasks").iterdir() if p.is_dir())
    want = a.tasks.split(",") if a.tasks else (None if cfg["tasks"] == "all" else cfg["tasks"])
    tasks = [t for t in all_tasks if not want or t.name in want]
    sides = [s for s in cfg["sides"] if not a.sides or s["name"] in a.sides.split(",")]
    until = a.until_exhausted or cfg.get("repeats") == "until_exhausted"
    repeats = a.repeats or (cfg.get("max_repeats", 100) if until else cfg["repeats"])
    out = ROOT / cfg["results_dir"]; out.mkdir(parents=True, exist_ok=True)
    results_path = out / "results.jsonl"
    print(f"tasks: {len(tasks)}  sides: {', '.join(s['name'] for s in sides)}  workers: {a.workers}  "
          f"{'until exhausted (max ' + str(repeats) + ' rounds)' if until else str(repeats) + ' rounds'}", flush=True)

    sched = Scheduler(cfg, sides, [(rep, t) for rep in range(1, repeats + 1) for t in tasks])
    if a.resume and results_path.exists():
        with open(results_path, encoding="utf-8") as f:
            finished = {(r["side"], r["task"], r["repeat"]) for r in map(json.loads, filter(str.strip, f)) if not r["capped"]}
        for s in sides:
            st = sched.st[s["name"]]
            st["pending"] = deque(j for j in st["pending"] if (s["name"], j[1].name, j[0]) not in finished)
        print("resume: " + ", ".join(f"{n} {len(st['pending'])} jobs left" for n, st in sched.st.items()), flush=True)

    def worker():
        while (job := sched.next_job()) is not None:
            side, rep, task = job
            try:
                row = run_one(cfg, side, task, rep, results_path)
            except Exception as e:  # keep the other workers going; the job is lost, not retried
                print(f"  {side['name']} {task.name} r{rep}: runner error {e!r}", flush=True)
                row = {"capped": False}
            sched.report(side, rep, task, row)

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(max(a.workers, 1))]
    for t in threads:
        t.start()
    try:
        for t in threads:
            while t.is_alive():
                t.join(1)
    except KeyboardInterrupt:
        sys.exit("\ninterrupted — finished runs are in results.jsonl; rerun analyze.py")
    print(f"\ndone. results: {results_path}\nnext: python analyze.py --config {a.config}")


if __name__ == "__main__":
    main()
