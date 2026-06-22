import datetime
import logging
import os
import re
import shutil
import sys
import tempfile
from typing import Optional

import db as _db

import discord
from discord import app_commands, FFmpegPCMAudio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv(dotenv_path='keys.env')

SOUNDS_BASE = os.environ.get('SOUNDS_BASE', '/var/chips')
ADMIN_ID = int(os.environ.get('ADMIN_ID') or '0')

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
    if not target.startswith(server_dir + os.sep):
        return None
    return target


def _log_play(interaction: discord.Interaction, sound_name: str) -> None:
    server_id = str(interaction.guild.id)
    server_name = interaction.guild.name
    user_id = str(interaction.user.id)
    username = str(interaction.user)
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
    await client.tree.sync()
    await client.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, name="/sound"
    ))
    logger.info('Bot logged in as: %s', client.user)


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
                value="Join a voice channel and type `/sound [name]` — autocomplete shows your sounds as you type.",
                inline=False,
            )
            embed.add_field(
                name="Other commands",
                value="`/soundlist` — see all sounds\n`/rmsound [name]` — delete a sound\n`/info` — full command list",
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


@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        msg = "You don't have permission to use that command."
    elif isinstance(error, app_commands.CheckFailure):
        msg = "You are not authorised to use this command."
    else:
        logger.exception('Unhandled app command error', exc_info=error)
        msg = "Something went wrong. Please try again."
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)


@client.event
async def on_voice_state_update(member, before, after):
    vc = member.guild.voice_client
    if vc is not None and len(vc.channel.members) == 1:
        await vc.disconnect()


# ---------------------------------------------------------------------------
# Sound commands
# ---------------------------------------------------------------------------

async def sound_autocomplete(interaction: discord.Interaction, current: str):
    if interaction.guild is None:
        return []
    server_dir = os.path.join(SOUNDS_BASE, str(interaction.guild.id))
    if not os.path.isdir(server_dir):
        return []
    names = sorted(f[:-4] for f in os.listdir(server_dir) if f.endswith('.mp3'))
    return [
        app_commands.Choice(name=n, value=n)
        for n in names if current.lower() in n.lower()
    ][:25]


@client.tree.command(name='sound', description='Play a sound in your voice channel')
@app_commands.autocomplete(sound_name=sound_autocomplete)
async def sound(interaction: discord.Interaction, sound_name: str):
    path = safe_sound_path(interaction.guild.id, sound_name)
    if path is None or not os.path.isfile(path):
        await interaction.response.send_message("That chip does not exist.", ephemeral=True)
        return
    if interaction.user.voice is None:
        await interaction.response.send_message("Please join a voice channel first!", ephemeral=True)
        return

    await interaction.response.defer()
    author_channel = interaction.user.voice.channel
    source = FFmpegPCMAudio(path)
    vc = interaction.guild.voice_client

    if vc is None:
        vc = await author_channel.connect()
    elif vc.channel != author_channel:
        if vc.is_playing():
            vc.stop()
        await vc.move_to(author_channel)

    if vc.is_playing():
        vc.stop()
    vc.play(source)
    _log_play(interaction, sound_name)
    await interaction.followup.send(f"▶ **{sound_name}**")


@client.tree.command(name='soundlist', description='List all sounds available in this server')
async def soundlist(interaction: discord.Interaction):
    server_dir = os.path.join(SOUNDS_BASE, str(interaction.guild.id))
    if not os.path.isdir(server_dir):
        await interaction.response.send_message(f"No sounds uploaded yet. Visit {UPLOAD_URL} to add some!")
        return
    names = sorted(f[:-4] for f in os.listdir(server_dir) if f.endswith('.mp3'))
    if not names:
        await interaction.response.send_message("No sounds found for this server.")
        return

    header = "Available Sounds:\n----------------------------\n"
    body = "  ".join(names)
    msg = f"```{header}{body}```"
    if len(msg) <= 2000:
        await interaction.response.send_message(msg)
        return

    # Chunk across multiple messages if too many sounds to fit
    await interaction.response.defer()
    chunks, chunk = [], header
    for name in names:
        if len(chunk) + len(name) + 2 > 1990:
            chunks.append(f"```{chunk}```")
            chunk = ""
        chunk += name + "  "
    if chunk:
        chunks.append(f"```{chunk}```")
    await interaction.followup.send(chunks[0])
    for c in chunks[1:]:
        await interaction.followup.send(c)


@client.tree.command(name='rmsound', description='Remove a sound (requires Manage Server permission)')
@app_commands.default_permissions(manage_guild=True)
@app_commands.autocomplete(sound_name=sound_autocomplete)
async def rmsound(interaction: discord.Interaction, sound_name: str):
    path = safe_sound_path(interaction.guild.id, sound_name)
    if path is None:
        await interaction.response.send_message("Invalid sound name.", ephemeral=True)
        return
    if not os.path.isfile(path):
        await interaction.response.send_message(f"`{sound_name}` does not exist.", ephemeral=True)
        return
    os.remove(path)
    await interaction.response.send_message(f"`{sound_name}` has been removed.")


@client.tree.command(name='leave', description='Make the bot leave the voice channel')
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("I left the channel.")
    else:
        await interaction.response.send_message("I am not in a voice channel.", ephemeral=True)


# ---------------------------------------------------------------------------
# Info / utility commands
# ---------------------------------------------------------------------------

@client.tree.command(name='info', description='Introduction to ChipBot and its commands')
async def info_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(
        "```"
        "Hi! I am ChipBot — your custom soundboard for Discord.\n\n"
        "Commands:\n"
        "  /sound [name]    — Play a sound (with autocomplete)\n"
        "  /soundlist       — List all sounds for this server\n"
        "  /rmsound [name]  — Remove a sound (requires Manage Server)\n"
        "  /leave           — Make me leave the voice channel\n"
        "  /joke            — Get a random joke\n"
        "  /crypto [coin]   — Get a coin price + 30-day chart\n"
        "  /serverinfo      — Show server details\n"
        "  /ping            — Check bot latency\n"
        "  /space           — Get the current ISS location\n\n"
        f"Upload sounds at {UPLOAD_URL}"
        "```"
    )


@client.tree.command(name='ping', description='Check bot latency')
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f'Pong! — Latency: {round(client.latency * 1000)} ms')


@client.tree.command(name='serverinfo', description='Show server information')
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
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
    await interaction.response.send_message(embed=embed)


@client.tree.command(name='space', description='Get the current ISS location')
async def space(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        r = requests.get('http://api.open-notify.org/iss-now.json', timeout=10).json()
        ts = datetime.datetime.utcfromtimestamp(int(r['timestamp'])).strftime('%H:%M:%S - %d-%m-%Y')
        lat = r['iss_position']['latitude']
        lon = r['iss_position']['longitude']
        await interaction.followup.send(f"ISS LOCATION AT {ts}\n Latitude:  {lat}\n Longitude: {lon}")
    except (KeyError, requests.RequestException):
        await interaction.followup.send("Could not fetch ISS location right now.")


@client.tree.command(name='joke', description='Get a random joke')
async def joke(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        resp = requests.get(
            "https://v2.jokeapi.dev/joke/Miscellaneous,Dark,Pun?type=single", timeout=10
        ).json()
        await interaction.followup.send(resp['joke'])
    except (KeyError, requests.RequestException):
        await interaction.followup.send("Could not fetch a joke right now.")


@client.tree.command(name='crypto', description='Get a cryptocurrency price and 30-day chart')
@app_commands.describe(coin='Coin slug, e.g. bitcoin, ethereum')
async def crypto(interaction: discord.Interaction, coin: str):
    await interaction.response.defer()
    slug = coin.lower().replace(' ', '-')
    try:
        resp_info = requests.get(f"https://api.coincap.io/v2/assets/{slug}", timeout=10).json()
        resp_hist = requests.get(
            f"https://api.coincap.io/v2/assets/{slug}/history?interval=d1", timeout=10
        ).json()
        coin_name = resp_info['data']['name']
        price = round(float(resp_info['data']['priceUsd']), 2)

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

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
        plt.savefig(tmp_path)
        plt.close()

        with open(tmp_path, 'rb') as fh:
            await interaction.followup.send(
                f"{coin_name}/USD = ${price}",
                file=discord.File(fh, filename='chart.png'),
            )
        os.remove(tmp_path)
    except (KeyError, IndexError, requests.RequestException):
        await interaction.followup.send(
            f"Could not fetch data for `{coin}`. "
            "Make sure the coin slug is correct (e.g. `bitcoin`, `ethereum`)."
        )


# ---------------------------------------------------------------------------
# Admin commands
# ---------------------------------------------------------------------------

admin_group = app_commands.Group(name='admin', description='Admin commands (bot owner only)')


@admin_group.command(name='servers', description='List all servers with uploaded sounds')
async def admin_servers(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("You are not authorised to use this command.", ephemeral=True)
        return
    if not os.path.isdir(SOUNDS_BASE):
        await interaction.response.send_message("Sounds directory not found.", ephemeral=True)
        return
    server_ids = sorted(
        d for d in os.listdir(SOUNDS_BASE)
        if os.path.isdir(os.path.join(SOUNDS_BASE, d))
    )
    await interaction.response.send_message(
        "  ".join(server_ids) if server_ids else "No servers found.",
        ephemeral=True,
    )


@admin_group.command(name='tier', description='Set the tier for a server')
@app_commands.describe(server_id='Discord server ID')
@app_commands.choices(tier=[
    app_commands.Choice(name='Basic (25 sounds)', value='basic'),
    app_commands.Choice(name='Pro (50 sounds)', value='pro'),
    app_commands.Choice(name='Premium (200 sounds)', value='premium'),
])
async def admin_tier(interaction: discord.Interaction, server_id: str, tier: app_commands.Choice[str]):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("You are not authorised to use this command.", ephemeral=True)
        return
    try:
        _db.set_tier(server_id, tier.value)
        limit = _db.TIERS[tier.value]
        await interaction.response.send_message(
            f"Server `{server_id}` set to **{tier.name}** ({limit} sounds).",
            ephemeral=True,
        )
    except ValueError as e:
        await interaction.response.send_message(str(e), ephemeral=True)


@admin_group.command(name='broadcast', description='Send a message to all servers')
@app_commands.describe(message='Message to broadcast to every server')
async def admin_broadcast(interaction: discord.Interaction, message: str):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("You are not authorised to use this command.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
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
    await interaction.followup.send(f"Broadcast sent to {sent} server(s). Failed: {failed}.")


client.tree.add_command(admin_group)


@client.tree.command(name='storage', description='Show disk usage (admin only)')
async def storage(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("You are not authorised to use this command.", ephemeral=True)
        return
    total, used, free = shutil.disk_usage('/')
    gb = 1024 ** 3
    await interaction.response.send_message(
        f"**Disk Usage:**\n"
        f" Used:  {used // gb} GB\n"
        f" Free:  {free // gb} GB\n"
        f" Total: {total // gb} GB",
        ephemeral=True,
    )


client.run(os.environ.get('TOKEN'), log_handler=None)
