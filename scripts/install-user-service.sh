#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BOT_HOME="$(cd -- "$SCRIPT_DIR/.." && pwd)"
SERVICE_NAME="openclaw-power-bot.service"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/$SERVICE_NAME"

mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=OpenClaw Power Discord Bot (LLM-free)
After=network-online.target

[Service]
Type=simple
Environment=BOT_HOME=$BOT_HOME
Environment=ENV_FILE=%h/.config/openclaw-power-bot.env
ExecStart=$BOT_HOME/scripts/run.sh
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
SERVICE

systemctl --user daemon-reload
systemctl --user enable --now "$SERVICE_NAME"
systemctl --user status "$SERVICE_NAME" --no-pager

echo "Installed: $SERVICE_FILE"
