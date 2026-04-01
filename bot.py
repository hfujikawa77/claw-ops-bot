#!/usr/bin/env python3
import os
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands

ALLOWED_USER_IDS = {int(x) for x in os.getenv('ALLOWED_USER_IDS', '').split(',') if x.strip().isdigit()}
ALLOWED_CHANNEL_IDS = {int(x) for x in os.getenv('ALLOWED_CHANNEL_IDS', '').split(',') if x.strip().isdigit()}
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!oc')
QT_PREFIX = os.getenv('QT_PREFIX', '!qt')
CC_PREFIX = os.getenv('CC_PREFIX', '!cc')
CX_PREFIX = os.getenv('CX_PREFIX', '!cx')
PB_PREFIX = os.getenv('PB_PREFIX', '!pb')
CLAUDE_CMD = os.getenv('CLAUDE_CMD', 'claude')
CODEX_CMD = os.getenv('CODEX_CMD', 'codex')
QT_URL_FILE = os.getenv('URL_OUTPUT_FILE', '')
STOP_CONFIRM_SECONDS = int(os.getenv('STOP_CONFIRM_SECONDS', '30'))
BOT_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_MAP = {
    'kimi': 'openrouter/moonshotai/kimi-k2.5',
    'codex': 'openai-codex/gpt-5.3-codex',
    'trinity': 'openrouter/arcee-ai/trinity-large-preview:free',
}

token = os.getenv('DISCORD_BOT_TOKEN', '').strip()
if not token:
    raise SystemExit('DISCORD_BOT_TOKEN is required')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX + ' ', intents=intents, help_command=None)

pending_stop = {}  # user_id -> expiry datetime


def authorized(ctx: commands.Context) -> bool:
    return authorized_message(ctx.message)


def authorized_message(message: discord.Message) -> bool:
    if ALLOWED_USER_IDS and message.author.id not in ALLOWED_USER_IDS:
        return False
    if ALLOWED_CHANNEL_IDS and message.channel.id not in ALLOWED_CHANNEL_IDS:
        return False
    return True


async def run_cmd(*cmd: str, timeout: int = 12, cwd: str | None = None) -> tuple[int, str]:
    p = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        out, err = await asyncio.wait_for(p.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        p.kill()
        return 124, f'timeout: {' '.join(cmd)}'
    text = (out or b'').decode(errors='ignore') + (err or b'').decode(errors='ignore')
    return p.returncode, text.strip() or '(no output)'


async def gateway_status_text() -> str:
    rc, out = await run_cmd('systemctl', '--user', 'is-active', 'openclaw-gateway.service')
    st = 'running' if rc == 0 and out.strip() == 'active' else 'stopped'
    return f'STATUS: {st}'


async def recent_gateway_logs(lines: int = 8) -> str:
    rc, out = await run_cmd('journalctl', '--user', '-u', 'openclaw-gateway.service', '-n', str(lines), '--no-pager')
    if rc != 0:
        return out[:1500]
    return out[:1500]


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} ({bot.user.id})')


@bot.command(name='help')
async def _help(ctx: commands.Context):
    if not authorized(ctx):
        return
    await ctx.reply(
        f'`{COMMAND_PREFIX}`: `status | start | stop | stop confirm | restart | logs | cl | ml | ms <key>`\n'
        f'`{PB_PREFIX}`: `refresh`\n'
        f'`{QT_PREFIX}`: `restart | url`',
        mention_author=False,
    )


@bot.command(name='status')
async def _status(ctx: commands.Context):
    if not authorized(ctx):
        return
    await ctx.reply(await gateway_status_text(), mention_author=False)


@bot.command(name='start')
async def _start(ctx: commands.Context):
    if not authorized(ctx):
        return
    rc, out = await run_cmd('systemctl', '--user', 'start', 'openclaw-gateway.service')
    st = await gateway_status_text()
    if out.strip() == '(no output)':
        out = await recent_gateway_logs(8)
    await ctx.reply(f"{'OK' if rc == 0 else 'NG'} start\n{st}\n```\n{out[:1500]}\n```", mention_author=False)


@bot.command(name='restart')
async def _restart(ctx: commands.Context):
    if not authorized(ctx):
        return
    rc, out = await run_cmd('systemctl', '--user', 'restart', 'openclaw-gateway.service')
    st = await gateway_status_text()
    if out.strip() == '(no output)':
        out = await recent_gateway_logs(8)
    await ctx.reply(f"{'OK' if rc == 0 else 'NG'} restart\n{st}\n```\n{out[:1500]}\n```", mention_author=False)


@bot.command(name='stop')
async def _stop(ctx: commands.Context, *args):
    if not authorized(ctx):
        return
    if len(args) == 1 and args[0].lower() == 'confirm':
        exp = pending_stop.get(ctx.author.id)
        if not exp or datetime.utcnow() > exp:
            await ctx.reply('stop confirmation expired. run `!oc stop` again.', mention_author=False)
            return
        pending_stop.pop(ctx.author.id, None)
        rc, out = await run_cmd('systemctl', '--user', 'stop', 'openclaw-gateway.service')
        st = await gateway_status_text()
        if out.strip() == '(no output)':
            out = await recent_gateway_logs(8)
        await ctx.reply(f"{'OK' if rc == 0 else 'NG'} stop\n{st}\n```\n{out[:1500]}\n```", mention_author=False)
        return

    pending_stop[ctx.author.id] = datetime.utcnow() + timedelta(seconds=STOP_CONFIRM_SECONDS)
    await ctx.reply(
        f'Confirm stop: run `!oc stop confirm` within {STOP_CONFIRM_SECONDS}s',
        mention_author=False,
    )


@bot.command(name='logs')
async def _logs(ctx: commands.Context):
    if not authorized(ctx):
        return
    rc, out = await run_cmd('journalctl', '--user', '-u', 'openclaw-gateway.service', '-n', '20', '--no-pager')
    prefix = 'OK' if rc == 0 else 'NG'
    await ctx.reply(f'{prefix} logs\n```\n{out[:1800]}\n```', mention_author=False)


@bot.command(name='cl')
async def _cron_list(ctx: commands.Context):
    if not authorized(ctx):
        return
    rc, out = await run_cmd('openclaw', 'cron', 'list')
    prefix = 'OK' if rc == 0 else 'NG'
    await ctx.reply(f'{prefix} cron list\n```\n{out[:1800]}\n```', mention_author=False)


@bot.command(name='ml')
async def _models_list(ctx: commands.Context):
    if not authorized(ctx):
        return
    rc, out = await run_cmd('openclaw', 'models', 'list')
    prefix = 'OK' if rc == 0 else 'NG'
    await ctx.reply(f'{prefix} models list\n```\n{out[:1800]}\n```', mention_author=False)


@bot.command(name='ms')
async def _models_set(ctx: commands.Context, key: str = ''):
    if not authorized(ctx):
        return
    model_name = MODEL_MAP.get(key)
    if not model_name:
        keys = ', '.join(f'`{k}`' for k in MODEL_MAP)
        await ctx.reply(f'Unknown model key. Available: {keys}', mention_author=False)
        return
    rc, out = await run_cmd('openclaw', 'models', 'set', model_name)
    prefix = 'OK' if rc == 0 else 'NG'
    await ctx.reply(f'{prefix} models set `{model_name}`\n```\n{out[:1800]}\n```', mention_author=False)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)

    text = message.content.strip()
    if text.startswith(CC_PREFIX + ' '):
        if not authorized_message(message):
            return
        rest = text[len(CC_PREFIX):].strip()
        cwd = None
        if rest.startswith('-C '):
            parts = rest[3:].split(None, 1)
            if len(parts) < 2:
                await message.reply('Usage: `!cc -C /path/to/dir prompt`', mention_author=False)
                return
            cwd, rest = parts
            if not os.path.isdir(cwd):
                await message.reply(f'Not a directory: `{cwd}`', mention_author=False)
                return
        prompt = rest
        await message.add_reaction('⏳')
        rc, out = await run_cmd(CLAUDE_CMD, '-p', prompt, timeout=120, cwd=cwd)
        await message.remove_reaction('⏳', bot.user)
        prefix = 'OK' if rc == 0 else 'NG'
        await message.reply(f'{prefix}\n{out[:1800]}', mention_author=False)
        return

    if text.startswith(CX_PREFIX + ' '):
        if not authorized_message(message):
            return
        rest = text[len(CX_PREFIX):].strip()
        cwd = None
        if rest.startswith('-C '):
            parts = rest[3:].split(None, 1)
            if len(parts) < 2:
                await message.reply('Usage: `!cx -C /path/to/dir prompt`', mention_author=False)
                return
            cwd, rest = parts
            if not os.path.isdir(cwd):
                await message.reply(f'Not a directory: `{cwd}`', mention_author=False)
                return
        prompt = rest
        await message.add_reaction('⏳')
        rc, out = await run_cmd(CODEX_CMD, 'exec', '--skip-git-repo-check', prompt, timeout=120, cwd=cwd)
        await message.remove_reaction('⏳', bot.user)
        # codex 出力から回答本文だけを抽出（"\ncodex\n" と "\ntokens used" の間）
        marker = '\ncodex\n'
        end_marker = '\ntokens used'
        if marker in out:
            body = out.split(marker, 1)[1]
            if end_marker in body:
                body = body.split(end_marker, 1)[0]
            reply_text = body.strip()
        else:
            reply_text = ('NG\n' if rc != 0 else '') + out[:1800]
        await message.reply(reply_text[:1800] or '(no output)', mention_author=False)
        return

    if text.startswith(PB_PREFIX + ' ') or text == PB_PREFIX:
        if not authorized_message(message):
            return
        args = text[len(PB_PREFIX):].strip().split()
        if args == ['refresh']:
            rc_pull, out_pull = await run_cmd('git', 'pull', cwd=BOT_DIR)
            await message.reply(
                f"{'OK' if rc_pull == 0 else 'NG'} git pull\n```\n{out_pull[:1800]}\n```\nrestarting...",
                mention_author=False,
            )
            await run_cmd('systemctl', '--user', 'restart', 'claw-ops-bot.service')
        else:
            await message.reply(f'Commands: `{PB_PREFIX} refresh`', mention_author=False)
        return

    # !qt コマンド: quick-tunnel サービスの操作
    if text.startswith(QT_PREFIX + ' ') or text == QT_PREFIX:
        if not authorized_message(message):
            return
        args = text[len(QT_PREFIX):].strip().split()
        if args == ['restart']:
            # quick-tunnel サービスを再起動する
            rc, out = await run_cmd('systemctl', '--user', 'restart', 'quick-tunnel.service')
            await message.reply(
                f"{'OK' if rc == 0 else 'NG'} qt restart\n```\n{out[:1800]}\n```",
                mention_author=False,
            )
        elif args == ['url']:
            # トンネルの公開 URL をファイルから読み取って返す
            if not QT_URL_FILE:
                await message.reply('QT_URL_FILE is not configured', mention_author=False)
            else:
                try:
                    with open(QT_URL_FILE) as f:
                        url = f.read().strip()
                    await message.reply(url or '(empty)', mention_author=False)
                except FileNotFoundError:
                    await message.reply('URL file not found', mention_author=False)
        else:
            # サブコマンドが不正な場合はヘルプを表示する
            await message.reply(f'Commands: `{QT_PREFIX} restart | url`', mention_author=False)


bot.run(token)
