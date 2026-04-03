# claw-ops-bot

DiscordからOpenClaw Gatewayを直接制御する専用Bot。PCを開かずにOpenClaw運用できます。  
<img width="300"  alt="image" src="https://github.com/user-attachments/assets/5820041b-98b7-439b-b357-7926b8f6fd0c" />
<img width="350" alt="image" src="https://github.com/user-attachments/assets/109bff7a-b582-42b0-bee4-bf0cc074cbf1" />

## Commands

| コマンド | 説明 |
|---|---|
| `!oc status` | Gateway の稼働状態確認 |
| `!oc start` | Gateway 起動 |
| `!oc restart` | Gateway 再起動 |
| `!oc stop` → `!oc stop confirm` | Gateway 停止（30秒以内に確認） |
| `!oc logs` | Gateway の最新ログ表示 |
| `!oc cl` | `openclaw cron list` |
| `!oc ml` | `openclaw models list` |
| `!oc ms <key>` | `openclaw models set`（key: `kimi` / `codex` / `trinity`） |
| `!pb refresh` | Bot を `git pull` で最新化して再起動 |
| `!qt restart` | quick-tunnel 再起動 |
| `!qt url` | quick-tunnel の現在のURL表示 |

## Setup
```bash
git clone https://github.com/hfujikawa77/claw-ops-bot.git
cd claw-ops-bot
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example ~/.config/claw-ops-bot.env
# edit ~/.config/claw-ops-bot.env
chmod +x scripts/run.sh scripts/install-user-service.sh
```

## 起動 / サービス登録

### Run (manual)
```bash
cd /path/to/claw-ops-bot
BOT_HOME="$(pwd)" ./scripts/run.sh
```

### Run as systemd --user（サービス登録 + 起動）
```bash
cd /path/to/claw-ops-bot
./scripts/install-user-service.sh
```

> `install-user-service.sh` は実行時のディレクトリから絶対パスを解決して、
> `~/.config/systemd/user/claw-ops-bot.service` を自動生成します。

## 再起動

```bash
systemctl --user restart claw-ops-bot.service
```

## 停止 / サービス登録解除

### アプリ停止
```bash
systemctl --user stop claw-ops-bot.service
systemctl --user status claw-ops-bot.service --no-pager
```

### systemd --user サービス登録解除
```bash
systemctl --user disable claw-ops-bot.service
rm -f ~/.config/systemd/user/claw-ops-bot.service
systemctl --user daemon-reload
systemctl --user reset-failed
```

### （任意）手動起動プロセスの停止
```bash
pkill -f "python(3)? bot\.py" || true
```

## Discord Bot 作成手順（Private運用）
1. Discord Developer Portal: <https://discord.com/developers/applications>
2. `New Application` → 名前入力（例: `claw-ops-bot`）
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

> **⚠️ セキュリティ上の注意**
> `ALLOWED_USER_IDS` と `ALLOWED_CHANNEL_IDS` は**必ず設定してください**。
> 未設定の場合、Botが参加しているチャンネルの**誰でも** `systemctl restart`・`git pull`・`claude -p` などのコマンドを実行できてしまいます。

## 運用確認コマンド
Discordで以下を実行:
- `!oc status`
- `!oc stop` → `!oc stop confirm`
- `!oc start`
- `!oc restart`
- `!oc logs`

## License
MIT

## Notes
- OpenClaw本体停止中でも、このBotが生きていれば `!oc start` で復旧可能。
- トラブル時ログ: `journalctl --user -u claw-ops-bot.service -n 100 --no-pager`
