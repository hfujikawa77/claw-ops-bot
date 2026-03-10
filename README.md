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

## 停止 / サービス登録解除

### アプリ停止
```bash
systemctl --user stop openclaw-power-bot.service
systemctl --user status openclaw-power-bot.service --no-pager
```

### systemd --user サービス登録解除
```bash
systemctl --user disable openclaw-power-bot.service
rm -f ~/.config/systemd/user/openclaw-power-bot.service
systemctl --user daemon-reload
systemctl --user reset-failed
```

### （任意）手動起動プロセスの停止
```bash
pkill -f "python(3)? bot\.py" || true
```

## Discord Bot 作成手順（Private運用）
1. Discord Developer Portal: <https://discord.com/developers/applications>
2. `New Application` → 名前入力（例: `openclaw-power-bot`）
3. 左メニュー `Bot` → `Add Bot`
4. `Reset Token` でトークン発行（`DISCORD_BOT_TOKEN` に設定）
5. `Message Content Intent` を **ON**

### Private App での注意（保存エラー対策）
`Installation` 画面で次を設定して保存:
- `Install Link` = `None`

> エラー: 「プライベートアプリケーションはデフォルトの認証リンクを持つことはできません」
> が出る場合は、上記 `Install Link=None` を先に設定する。

### サーバーへ招待
1. `OAuth2 > URL Generator`
2. `Scopes`: `bot`
3. `Bot Permissions`（最小）:
   - `View Channels`
   - `Send Messages`
   - `Read Message History`
4. 生成されたURLでサーバーへ招待

### IDの取得（allowlist用）
Discordの `Developer Mode` をONにしてコピー:
- ユーザーID: 自分を右クリック → `Copy User ID`
- チャンネルID: 対象チャンネルを右クリック → `Copy Channel ID`

`.env` 例:
```env
ALLOWED_USER_IDS=<YOUR_DISCORD_USER_ID>
ALLOWED_CHANNEL_IDS=<YOUR_DISCORD_CHANNEL_ID>
```

## 運用確認コマンド
Discordで以下を実行:
- `!oc status`
- `!oc stop` → `!oc stop confirm`
- `!oc start`
- `!oc restart`
- `!oc logs`

## Notes
- OpenClaw本体停止中でも、このBotが生きていれば `!oc start` で復旧可能。
- 既存 `openclaw-power-web` とは非依存。
- トラブル時ログ: `journalctl --user -u openclaw-power-bot.service -n 100 --no-pager`
