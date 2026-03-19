#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_BOT_HOME="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BOT_HOME="${BOT_HOME:-$DEFAULT_BOT_HOME}"
ENV_FILE="${ENV_FILE:-$HOME/.config/claw-ops-bot.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ ! -x "$BOT_HOME/.venv/bin/python" ]]; then
  echo "[ERROR] Python venv not found: $BOT_HOME/.venv/bin/python" >&2
  echo "Run setup first: python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

exec "$BOT_HOME/.venv/bin/python" "$BOT_HOME/bot.py"
