# Sandbox for the agent suite: agents run with `opencode run --auto` (unattended shell access),
# so run the whole thing in here rather than on your machine.
#
#   docker build -t plan-bench-agent .
#   docker run --rm -it -v "$PWD:/suite" -e DEEPINFRA_API_KEY -e CMD_API_KEY plan-bench-agent bash run.sh
#
FROM node:22-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv git ca-certificates curl procps \
 && rm -rf /var/lib/apt/lists/*

RUN npm install -g opencode-ai@1.19.5 && opencode --version

# `python` on PATH is what the agents and graders call
RUN python3 -m venv /venv && /venv/bin/pip install --no-cache-dir requests==2.32.3 pytest==8.3.4
ENV PATH=/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /suite
CMD ["bash", "run.sh"]
