# openclaw-power-bot

DiscordからOpenClaw Gatewayを直接制御する専用Bot（LLM非経由）。

## Commands
- `!oc status`
- `!oc start`
- `!oc restart`
- `!oc stop` → `!oc stop confirm`（30秒以内）
- `!oc logs`

## Setup
```bash
cd ~/.openclaw/workspace/GitHub/openclaw-power-bot
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example ~/.config/openclaw-power-bot.env
# edit ~/.config/openclaw-power-bot.env
```

## Run (manual)
```bash
cd ~/.openclaw/workspace/GitHub/openclaw-power-bot
. .venv/bin/activate
set -a; source ~/.config/openclaw-power-bot.env; set +a
python bot.py
```

## Run as systemd --user
```bash
mkdir -p ~/.config/systemd/user
cp systemd/openclaw-power-bot.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now openclaw-power-bot.service
systemctl --user status openclaw-power-bot.service --no-pager
```

## Notes
- OpenClaw本体停止中でも、このBotが生きていれば `!oc start` で復旧可能。
- 既存 `openclaw-power-web` とは非依存。
