import os
import random
import datetime
import discord
from discord.ext import tasks, commands
from discord import TextChannel, app_commands
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
import pytz

load_dotenv()


def require_env(name):
    val = os.getenv(name)
    if val is None:
        raise ValueError(f"{name} is not set in environment")
    return val


DISCORD_TOKEN = require_env("DISCORD_TOKEN")
SPOTIFY_CLIENT_ID = require_env("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = require_env("SPOTIFY_CLIENT_SECRET")
PLAYLIST_ID = require_env("SPOTIFY_PLAYLIST_ID")
CHANNEL_ID = int(require_env("DISCORD_CHANNEL_ID"))

spot = Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET
    )
)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


def get_random_song():
    results = spot.playlist_tracks(PLAYLIST_ID)
    if not results or "items" not in results:
        raise RuntimeError("Failed to fetch playlist tracks or playlist is empty")

    tracks = results["items"]
    while results["next"]:
        results = spot.next(results)
        if not results or "items" not in results:
            break
        tracks.extend(results["items"])

    # TODO: Make sure same track is never posted twice. SQLite?
    track = random.choice(tracks)["track"]
    name = track["name"]
    artists = ", ".join(a["name"] for a in track["artists"])
    url = track["external_urls"]["spotify"]
    return f"🎵 [**{name}**]({url}) by *{artists}*"


@tasks.loop(time=datetime.time(hour=16, tzinfo=pytz.timezone("Europe/Helsinki")))
async def daily_song():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if channel and isinstance(channel, TextChannel):
        song_msg = get_random_song()
        await channel.send(song_msg)


@bot.event
async def on_ready():
    await bot.tree.sync()
    if not daily_song.is_running():
        daily_song.start()
    print(f"Logged in as {bot.user}")


def is_admin_or_owner_user():
    # tmp permission checker
    async def predicate(interaction: discord.Interaction) -> bool:
        user = interaction.user
        if isinstance(user, discord.Member) and user.guild_permissions.administrator:
            return True
        if user.id == 197033067255169025:
            return True
        return False

    return app_commands.check(predicate)


@bot.tree.command(
    name="spotifybiisi",
    description="Send a random song immediately from the playlist",
)
@is_admin_or_owner_user()
async def test_song(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    channel = bot.get_channel(CHANNEL_ID)
    if isinstance(channel, TextChannel):
        try:
            song_msg = get_random_song()
            await interaction.followup.send(
                f"Tämän päivän huippubiisi on: {song_msg} \n-# Biisit haetaan Perjantai-illan [Spotify-listalta](<https://open.spotify.com/playlist/6QSn6IOxMqCyZC2gqLoFci?si=d05c3e7cc79b47d4>)"
            )
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)
    else:
        await interaction.response.send_message("Invalid channel", ephemeral=True)


bot.run(DISCORD_TOKEN)
