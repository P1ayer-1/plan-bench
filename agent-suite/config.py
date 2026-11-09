"""Config loading with `"extends": "<path>"`: the file deep-merges over its base, and `sides` merge by
name (a side listed in the overlay but not the base is added). Lets dev/mock_config.json reuse the
real suite_config.json and override only endpoints and paths."""
import json
from pathlib import Path


def _merge(base, over):
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = _merge(base[k], v) if k in base else v
        return out
    return over


def load_config(path):
    path = Path(path)
    cfg = json.loads(path.read_text(encoding="utf-8"))
    ext = cfg.pop("extends", None)
    if not ext:
        return cfg
    base = load_config((path.parent / ext).resolve())
    over_sides = {s["name"]: s for s in cfg.pop("sides", [])}
    merged = _merge(base, cfg)
    sides = [_merge(s, over_sides.pop(s["name"])) if s["name"] in over_sides else s for s in base.get("sides", [])]
    merged["sides"] = sides + list(over_sides.values())
    return merged
