import datetime
import logging
import os
import re
import shutil
import sys
from typing import Optional

import db as _db

import discord
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests
from discord import FFmpegPCMAudio
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv(dotenv_path='keys.env')

SOUNDS_BASE = os.environ.get('SOUNDS_BASE', '/var/chips')
ADMIN_ID = int(os.environ.get('ADMIN_ID') or '0')
RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '')

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S',
)
logger = logging.getLogger('chipbot')

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)


def safe_sound_path(server_id: int, sound_name: str) -> Optional[str]:
    """Return the absolute path to a sound file, or None if the name is unsafe.

    Prevents path traversal by enforcing an allowlist on the name and verifying
    the resolved path stays inside the server's subdirectory.
    """
    if not re.match(r'^[\w\-]+$', sound_name):
        return None
    server_dir = os.path.realpath(os.path.join(SOUNDS_BASE, str(server_id)))
    target = os.path.realpath(os.path.join(server_dir, sound_name + '.mp3'))
    # Ensure target is strictly inside server_dir
    if not target.startswith(server_dir + os.sep):
        return None
    return target


def _log_play(ctx, sound_name: str) -> None:
    server_id = str(ctx.guild.id)
    server_name = ctx.guild.name
    user_id = str(ctx.author.id)
    username = str(ctx.author)
    logger.info('PLAY server=%s (%s) user=%s (%s) sound=%s', server_id, server_name, user_id, username, sound_name)
    try:
        _db.log_play(server_id, server_name, user_id, username, sound_name)
    except Exception:
        logger.exception('Failed to write play event to DB')


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@client.event
async def on_ready():
    await client.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, name="!help"
    ))
    print(f'Bot logged in as: {client.user}')


UPLOAD_URL = os.environ.get('UPLOAD_URL', 'https://chipbot-production.up.railway.app')


@client.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="Hey, I'm ChipBot!",
                url=UPLOAD_URL,
                description="Your custom soundboard for Discord. Here's how to get started:",
                color=0x765E89,
            )
            embed.add_field(
                name="Upload sounds",
                value=(
                    f"Head to **[the upload site]({UPLOAD_URL})**, log in with Discord, "
                    "select this server, and upload an `.mp3` (max 400 KB)."
                ),
                inline=False,
            )
            embed.add_field(
                name="Play a sound",
                value="Join a voice channel and type `!sound [name]`.",
                inline=False,
            )
            embed.add_field(
                name="Other commands",
                value="`!soundlist` — see all sounds\n`!rmsound [name]` — delete a sound\n`!help` — full command list",
                inline=False,
            )
            await channel.send(embed=embed)
            break


@client.event
async def on_guild_remove(guild):
    server_dir = os.path.join(SOUNDS_BASE, str(guild.id))
    if os.path.isdir(server_dir):
        for f in os.listdir(server_dir):
            if f.endswith('.mp3'):
                os.remove(os.path.join(server_dir, f))
        try:
            os.rmdir(server_dir)
        except OSError:
            pass


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("That command was not found — try `!help` for available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: `{error.param.name}`. Check `!help` for usage.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use that command.")


@client.event
async def on_voice_state_update(member, before, after):
    vc = member.guild.voice_client
    if vc is not None and len(vc.channel.members) == 1:
        await vc.disconnect()


# ---------------------------------------------------------------------------
# Sound commands
# ---------------------------------------------------------------------------

@client.command(help='Play a sound: !sound [name]')
async def sound(ctx, sound_name: str):
    path = safe_sound_path(ctx.guild.id, sound_name)
    if path is None or not os.path.isfile(path):
        await ctx.send("That chip does not exist.")
        return
    if ctx.author.voice is None:
        await ctx.send("Please join a voice channel first!")
        return

    author_channel = ctx.author.voice.channel
    source = FFmpegPCMAudio(path)
    vc = ctx.voice_client

    if vc is None:
        vc = await author_channel.connect()
    elif vc.channel != author_channel:
        if vc.is_playing():
            vc.stop()
        await vc.move_to(author_channel)

    if vc.is_playing():
        vc.stop()
    vc.play(source)
    _log_play(ctx, sound_name)


@client.command(help='List all sounds available in this server')
async def soundlist(ctx):
    server_dir = os.path.join(SOUNDS_BASE, str(ctx.guild.id))
    if not os.path.isdir(server_dir):
        await ctx.send(f"No sounds uploaded yet. Visit {UPLOAD_URL} to add some!")
        return
    names = sorted(f[:-4] for f in os.listdir(server_dir) if f.endswith('.mp3'))
    if not names:
        await ctx.send("No sounds found for this server.")
        return
    await ctx.send("```Available Sounds:\n----------------------------\n" + "  ".join(names) + "```")


@client.command(help='Remove a sound (requires Manage Guild permission): !rmsound [name]')
@commands.has_permissions(manage_guild=True)
async def rmsound(ctx, sound_name: str):
    path = safe_sound_path(ctx.guild.id, sound_name)
    if path is None:
        await ctx.send("Invalid sound name.")
        return
    if not os.path.isfile(path):
        await ctx.send(f"`{sound_name}` does not exist.")
        return
    os.remove(path)
    await ctx.send(f"`{sound_name}` has been removed.")


@client.command(help='Make the bot leave the voice channel')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send("I left the channel.")
    else:
        await ctx.send("I am not in a voice channel.")


# ---------------------------------------------------------------------------
# Info / utility commands
# ---------------------------------------------------------------------------

@client.command(name='info', help='Introduction to ChipBot')
async def info_cmd(ctx):
    await ctx.send(
        "```"
        "Hi! I am ChipBot — your custom soundboard for Discord.\n\n"
        "Commands:\n"
        "  !sound [name]    — Play a sound\n"
        "  !soundlist       — List all sounds for this server\n"
        "  !rmsound [name]  — Remove a sound (requires Manage Guild)\n"
        "  !leave           — Make me leave the voice channel\n"
        "  !joke            — Get a random joke\n"
        "  !crypto [coin]   — Get a coin price + 30-day chart\n"
        "  !serverinfo      — Show server details\n"
        "  !ping            — Check bot latency\n"
        "  !space           — Get the current ISS location\n\n"
        f"Upload sounds at {UPLOAD_URL}"
        "```"
    )


@client.command(help='Check bot latency')
async def ping(ctx):
    await ctx.send(f'Pong! — Latency: {round(client.latency * 1000)} ms')


@client.command(help='Show server information')
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title=f"{guild.name} — Server Information",
        description=guild.description or "No description set",
        color=discord.Color.blue(),
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=str(guild.owner), inline=True)
    embed.add_field(name="Server ID", value=str(guild.id), inline=True)
    embed.add_field(name="Member Count", value=str(guild.member_count), inline=True)
    await ctx.send(embed=embed)


@client.command(help='Get the current ISS location')
async def space(ctx):
    try:
        r = requests.get('http://api.open-notify.org/iss-now.json', timeout=10).json()
        ts = datetime.datetime.utcfromtimestamp(int(r['timestamp'])).strftime('%H:%M:%S - %d-%m-%Y')
        lat = r['iss_position']['latitude']
        lon = r['iss_position']['longitude']
        await ctx.send(f"ISS LOCATION AT {ts}\n Latitude:  {lat}\n Longitude: {lon}")
    except (KeyError, requests.RequestException):
        await ctx.send("Could not fetch ISS location right now.")


@client.command(help='Get a random joke')
async def joke(ctx):
    try:
        resp = requests.get(
            "https://v2.jokeapi.dev/joke/Miscellaneous,Dark,Pun?type=single", timeout=10
        ).json()
        await ctx.send(resp['joke'])
    except (KeyError, requests.RequestException):
        await ctx.send("Could not fetch a joke right now.")


@client.command(help='Get a cryptocurrency price and 30-day chart: !crypto [coin]')
async def crypto(ctx, coin: str):
    slug = coin.lower().replace(' ', '-')
    try:
        resp_info = requests.get(f"https://api.coincap.io/v2/assets/{slug}", timeout=10).json()
        resp_hist = requests.get(
            f"https://api.coincap.io/v2/assets/{slug}/history?interval=d1", timeout=10
        ).json()
        coin_name = resp_info['data']['name']
        price = round(float(resp_info['data']['priceUsd']), 2)
        await ctx.send(f"{coin_name}/USD = ${price}")

        history = resp_hist['data'][1:30]
        dates = [e['date'] for e in history]
        values = [float(e['priceUsd']) for e in history]

        plt.figure()
        plt.plot(dates, values)
        plt.xticks([dates[0], dates[-1]])
        plt.xlabel('Date')
        plt.ylabel('Price (USD)')
        plt.title(f"{coin_name} — Last 30 days")
        plt.tight_layout()
        plt.savefig('chart.png')
        plt.close()

        with open('chart.png', 'rb') as fh:
            await ctx.send(file=discord.File(fh, filename='chart.png'))
        os.remove('chart.png')
    except (KeyError, IndexError, requests.RequestException):
        await ctx.send(
            f"Could not fetch data for `{coin}`. "
            "Make sure the coin slug is correct (e.g. `bitcoin`, `ethereum`)."
        )


# ---------------------------------------------------------------------------
# Admin commands
# ---------------------------------------------------------------------------

@client.command(help='Admin commands: s1 (list servers), tier <id> <tier>, broadcast <msg>')
async def admin(ctx, subcommand: str, *args):
    if ctx.author.id != ADMIN_ID:
        await ctx.send("You are not authorised to use this command.")
        return
    if subcommand == 's1':
        if not os.path.isdir(SOUNDS_BASE):
            await ctx.send("Sounds directory not found.")
            return
        server_ids = sorted(
            d for d in os.listdir(SOUNDS_BASE)
            if os.path.isdir(os.path.join(SOUNDS_BASE, d))
        )
        await ctx.send("  ".join(server_ids) if server_ids else "No servers found.")
    elif subcommand == 'broadcast':
        if not args:
            await ctx.send("Usage: `!admin broadcast <message>`")
            return
        message = ' '.join(args)
        sent, failed = 0, 0
        for guild in client.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(message)
                        sent += 1
                    except discord.HTTPException:
                        failed += 1
                    break
        await ctx.send(f"Broadcast sent to {sent} server(s). Failed: {failed}.")
    elif subcommand == 'tier':
        if len(args) != 2:
            await ctx.send("Usage: `!admin tier <server_id> <basic|pro|premium>`")
            return
        server_id, tier = args
        try:
            _db.set_tier(server_id, tier)
            limit = _db.TIERS[tier]
            await ctx.send(f"Server `{server_id}` set to **{tier.capitalize()}** tier ({limit} sounds).")
        except ValueError as e:
            await ctx.send(str(e))


@client.command(help='Show disk usage (admin only)')
async def storage(ctx):
    if ctx.author.id != ADMIN_ID:
        await ctx.send("You are not authorised to use this command.")
        return
    total, used, free = shutil.disk_usage('/')
    gb = 1024 ** 3
    await ctx.send(
        f"**VPS Disk Usage:**\n"
        f" Used:  {used // gb} GB\n"
        f" Free:  {free // gb} GB\n"
        f" Total: {total // gb} GB"
    )


client.run(os.environ.get('TOKEN'))
