import os
import random
from datetime import timezone, timedelta, time
import discord
from discord.ext import tasks, commands
from discord import TextChannel, app_commands
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

SONG_TEMPLATE = (
    "Tämän päivän huippubiisi on {song} \n"
    "-# Biisit haetaan Perjantai-illan [Spotify-listalta]"
    "(<https://open.spotify.com/playlist/6QSn6IOxMqCyZC2gqLoFci?si=d05c3e7cc79b47d4>)"
)


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
    return f"[**{name}**]({url}) artistilta {artists}"


@tasks.loop(time=time(hour=17, tzinfo=timezone(timedelta(hours=3))))
async def daily_song():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if channel and isinstance(channel, TextChannel):
        song_msg = get_random_song()
        msg = await channel.send(SONG_TEMPLATE.format(song=song_msg))
        for emoji in ("👍", "👎"):
            await msg.add_reaction(emoji)


@bot.event
async def on_ready():
    await bot.tree.sync()
    if not daily_song.is_running():
        daily_song.start()


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
            msg = await interaction.followup.send(
                SONG_TEMPLATE.format(song=song_msg), wait=True
            )
            for emoji in ("👍", "👎"):
                await msg.add_reaction(emoji)
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)
    else:
        await interaction.response.send_message("Invalid channel", ephemeral=True)


bot.run(DISCORD_TOKEN)
