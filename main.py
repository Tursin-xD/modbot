import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import os
from keep_alive import keep_alive

# --- INITIALIZATION ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # This syncs your slash commands with Discord
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

bot = MyBot()

# YouTube/FFmpeg Settings
YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True', 'quiet': True}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# --- 1. SMART MODERATION (Slash) ---
@bot.tree.command(name="clear", description="Delete a number of messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Deleted {amount} messages.")

# --- 2. MUSIC & PARTY (Slash) ---
@bot.tree.command(name="play", description="Play music from YouTube in a Voice or Stage channel")
async def play(interaction: discord.Interaction, search: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("Join a voice channel first!", ephemeral=True)

    await interaction.response.defer() # Gives the bot time to process the video
    
    # Connection Logic
    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()
        # Auto-Speaker for Stage
        if isinstance(interaction.user.voice.channel, discord.StageChannel):
            try:
                await interaction.guild.me.edit(suppress=False)
            except:
                pass

    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
        url2 = info['url']
        source = await discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
        vc.play(source)

    await interaction.followup.send(f"🎶 Now Playing: **{info['title']}**")

@bot.tree.command(name="leave", description="Stop music and leave the channel")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Left the channel.")
    else:
        await interaction.response.send_message("I'm not in a voice channel!", ephemeral=True)

# --- 3. SKILL BOT (XP System) ---
xp_data = {}

@bot.event
async def on_message(message):
    if message.author.bot: return
    uid = str(message.author.id)
    xp_data[uid] = xp_data.get(uid, 0) + 10
    await bot.process_commands(message)

@bot.tree.command(name="rank", description="Check your current XP")
async def rank(interaction: discord.Interaction):
    xp = xp_data.get(str(interaction.user.id), 0)
    await interaction.response.send_message(f"🏆 {interaction.user.mention}, you have **{xp} XP**!")

# --- 4. UTILITY (Slash) ---
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"📡 Latency: {round(bot.latency * 1000)}ms")

# --- LAUNCH ---
keep_alive()
bot.run(os.getenv('TOKEN'))
