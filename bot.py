#!/usr/bin/env python3
import os
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands

ALLOWED_USER_IDS = {int(x) for x in os.getenv('ALLOWED_USER_IDS', '').split(',') if x.strip().isdigit()}
ALLOWED_CHANNEL_IDS = {int(x) for x in os.getenv('ALLOWED_CHANNEL_IDS', '').split(',') if x.strip().isdigit()}
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!oc')
STOP_CONFIRM_SECONDS = int(os.getenv('STOP_CONFIRM_SECONDS', '30'))

token = os.getenv('DISCORD_BOT_TOKEN', '').strip()
if not token:
    raise SystemExit('DISCORD_BOT_TOKEN is required')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX + ' ', intents=intents, help_command=None)

pending_stop = {}  # user_id -> expiry datetime


def authorized(ctx: commands.Context) -> bool:
    if ALLOWED_USER_IDS and ctx.author.id not in ALLOWED_USER_IDS:
        return False
    if ALLOWED_CHANNEL_IDS and ctx.channel.id not in ALLOWED_CHANNEL_IDS:
        return False
    return True


async def run_cmd(*cmd: str) -> tuple[int, str]:
    p = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(p.communicate(), timeout=12)
    except asyncio.TimeoutError:
        p.kill()
        return 124, f'timeout: {' '.join(cmd)}'
    text = (out or b'').decode(errors='ignore') + (err or b'').decode(errors='ignore')
    return p.returncode, text.strip() or '(no output)'


async def gateway_status_text() -> str:
    rc, out = await run_cmd('systemctl', '--user', 'is-active', 'openclaw-gateway.service')
    st = 'running' if rc == 0 and out.strip() == 'active' else 'stopped'
    return f'STATUS: {st}'


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
    await ctx.reply(f"{'OK' if rc == 0 else 'NG'} start\n{st}\n```\n{out[:1500]}\n```", mention_author=False)


@bot.command(name='restart')
async def _restart(ctx: commands.Context):
    if not authorized(ctx):
        return
    rc, out = await run_cmd('systemctl', '--user', 'restart', 'openclaw-gateway.service')
    st = await gateway_status_text()
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


bot.run(token)
