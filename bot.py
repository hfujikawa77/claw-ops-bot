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
CLAUDE_CMD = os.getenv('CLAUDE_CMD', 'claude')
QT_URL_FILE = os.getenv('URL_OUTPUT_FILE', '')
STOP_CONFIRM_SECONDS = int(os.getenv('STOP_CONFIRM_SECONDS', '30'))

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


async def run_cmd(*cmd: str, timeout: int = 12) -> tuple[int, str]:
    p = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
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
        'Commands: `!oc status | start | stop | stop confirm | restart | logs`\n'
        f'Prefix: `{COMMAND_PREFIX}`',
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


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)

    text = message.content.strip()
    if text.startswith(CC_PREFIX + ' '):
        if not authorized_message(message):
            return
        prompt = text[len(CC_PREFIX):].strip()
        await message.add_reaction('⏳')
        rc, out = await run_cmd(CLAUDE_CMD, '-p', prompt, timeout=120)
        await message.remove_reaction('⏳', bot.user)
        prefix = 'OK' if rc == 0 else 'NG'
        await message.reply(f'{prefix}\n{out[:1800]}', mention_author=False)
        return

    if text.startswith(QT_PREFIX + ' ') or text == QT_PREFIX:
        if not authorized_message(message):
            return
        args = text[len(QT_PREFIX):].strip().split()
        if args == ['restart']:
            rc, out = await run_cmd('systemctl', '--user', 'restart', 'quick-tunnel.service')
            await message.reply(
                f"{'OK' if rc == 0 else 'NG'} qt restart\n```\n{out[:1800]}\n```",
                mention_author=False,
            )
        elif args == ['url']:
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
            await message.reply(f'Commands: `{QT_PREFIX} restart | url`', mention_author=False)


bot.run(token)
