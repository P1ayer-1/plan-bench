#!/usr/bin/env bash
# One-shot pipeline: preflight -> proxy (background) -> run_suite -> analyze.
# Extra arguments go to run_suite.py, e.g.  ./run.sh --tasks t01_tags --repeats 1
#   CONFIG=dev/mock_config.json ./run.sh      use another config
#   SKIP_PREFLIGHT=1 ./run.sh                 skip the live endpoint checks
set -euo pipefail
cd "$(dirname "$0")"
CONFIG="${CONFIG:-suite_config.json}"

if [[ -z "${SKIP_PREFLIGHT:-}" ]]; then
  python preflight.py --config "$CONFIG" || { echo "preflight found problems (see above); SKIP_PREFLIGHT=1 to run anyway"; exit 1; }
fi

python proxy.py --config "$CONFIG" &
PROXY=$!
trap 'kill $PROXY 2>/dev/null || true' EXIT
PORT=$(python -c "from config import load_config; print(load_config('$CONFIG').get('proxy_port', 8899))")
for _ in $(seq 1 30); do
  curl -sf "http://127.0.0.1:$PORT/_health" >/dev/null && break
  sleep 1
done

python run_suite.py --config "$CONFIG" "$@"
python analyze.py --config "$CONFIG"
