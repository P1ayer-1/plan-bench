"""Shared grading: hidden tests (or a custom grade.py) run against a finished workspace."""
import os, shutil, subprocess, sys

ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
from pathlib import Path


def _pytest(ws, target, timeout):
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(target)],
                           cwd=ws, capture_output=True, text=True, timeout=timeout, env=ENV)
        return p.returncode == 0, (p.stdout + p.stderr)[-1500:]
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"


def grade(task_dir: Path, ws: Path, timeout=180):
    """Return dict(passed, detail, visible_passed)."""
    task_dir, ws = Path(task_dir), Path(ws)
    custom = task_dir / "grade.py"
    if custom.exists():
        try:
            p = subprocess.run([sys.executable, str(custom), str(ws)], capture_output=True, text=True,
                               timeout=timeout * 3)
            passed, detail = p.returncode == 0, (p.stdout + p.stderr)[-1500:]
        except subprocess.TimeoutExpired:
            passed, detail = False, "grader timeout"
    else:
        dst = ws / f"_hidden_test_{task_dir.name}.py"
        shutil.copy(task_dir / "hidden_test.py", dst)
        try:
            passed, detail = _pytest(ws, dst.name, timeout)
        finally:
            dst.unlink(missing_ok=True)
    visible_passed, _ = _pytest(ws, "tests", timeout) if (ws / "tests").exists() else (None, "")
    return {"passed": passed, "detail": detail, "visible_passed": visible_passed}
