import discord, yt_dlp, os, threading, asyncio
from discord import app_commands
from discord.ext import commands
from google import genai
from flask import Flask

# --- 1. RAILWAY SYSTEM FIXES ---
# Manually inject the path so Railway finds FFmpeg
os.environ["PATH"] += os.pathsep + "/usr/bin" + os.pathsep + "/usr/local/bin"

app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. CONFIGURATION ---
OWNER_ID = 1459506686157914213
TOKEN = os.getenv('DISCORD_TOKEN')
AI_KEY = os.getenv('GEMINI_KEY')
COOKIE_DATA = os.getenv('YOUTUBE_COOKIES')

FFMPEG_PATH = "ffmpeg"
loop_status = {}

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
ai_client = genai.Client(api_key=AI_KEY) if AI_KEY else None

# --- 3. MUSIC ENGINE ---
async def get_info(query, is_url=False):
    loop = asyncio.get_event_loop()
    def fetch():
        opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'source_address': '0.0.0.0',
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
        }
        if COOKIE_DATA:
            opts['http_headers'] = {'Cookie': COOKIE_DATA}
            
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(query if is_url else f"ytsearch1:{query}", download=False)
    return await loop.run_in_executor(None, fetch)

def play_next(vc, guild_id, info):
    if loop_status.get(guild_id, False) and vc.is_connected():
        source = discord.FFmpegOpusAudio(info['url'], executable=FFMPEG_PATH)
        vc.play(source, after=lambda e: play_next(vc, guild_id, info))

# --- 4. THE 10 COMMANDS ---

@bot.tree.command(name="play", description="Play music")
async def play(itn: discord.Interaction, search: str, looped: bool = False):
    await itn.response.defer()
    if not itn.user.voice: return await itn.followup.send("Join a VC!")
    vc = itn.guild.voice_client or await itn.user.voice.channel.connect()
    if vc.is_playing(): vc.stop(); await asyncio.sleep(1)
    try:
        data = await get_info(search)
        target = data['entries'][0]
        # Railway-specific FFmpeg options for stability
        options = "-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        source = discord.FFmpegOpusAudio(target['url'], executable=FFMPEG_PATH, options=options)
        loop_status[itn.guild.id] = looped
        vc.play(source, after=lambda e: play_next(vc, itn.guild.id, target))
        await itn.followup.send(f"🎶 Now Playing: **{target['title']}**")
    except Exception as e: await itn.followup.send(f"❌ Error: {e}")

@bot.tree.command(name="ask", description="AI Chat")
async def ask(itn: discord.Interaction, question: str):
    if not ai_client: return await itn.response.send_message("AI Key missing.")
    await itn.response.defer()
    res = ai_client.models.generate_content(model="gemini-1.5-flash", contents=question)
    await itn.followup.send(f"🤖 {res.text[:1900]}")

@bot.tree.command(name="stop", description="Stop music")
async def stop(itn: discord.Interaction):
    if itn.guild.voice_client: await itn.guild.voice_client.disconnect()
    await itn.response.send_message("⏹️ Stopped.")

@bot.tree.command(name="clear", description="Clear messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(itn: discord.Interaction, amount: int):
    await itn.channel.purge(limit=amount)
    await itn.response.send_message(f"🧹 Done.", ephemeral=True)

@bot.tree.command(name="ping", description="Check latency")
async def ping(itn: discord.Interaction):
    await itn.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

@bot.tree.command(name="loop", description="Toggle loop")
async def loop(itn: discord.Interaction, status: bool):
    loop_status[itn.guild.id] = status
    await itn.response.send_message(f"🔁 Loop: {status}")

@bot.tree.command(name="serverinfo", description="Server stats")
async def serverinfo(itn: discord.Interaction):
    await itn.response.send_message(f"📊 {itn.guild.name}: {itn.guild.member_count} members.")

@bot.tree.command(name="userinfo", description="User stats")
async def userinfo(itn: discord.Interaction, member: discord.Member = None):
    m = member or itn.user
    await itn.response.send_message(f"👤 {m.name} | Joined: {m.joined_at.strftime('%Y-%m-%d')}")

@bot.tree.command(name="show", description="Watch Together")
async def show(itn: discord.Interaction):
    if not itn.user.voice: return await itn.response.send_message("Join VC!")
    inv = await itn.user.voice.channel.create_invite(target_type=discord.InviteTarget.embedded_application, target_application_id=880218394199220334)
    await itn.response.send_message(f"🎬 {inv.url}")

@bot.tree.command(name="sync", description="Force sync commands")
async def sync_cmd(itn: discord.Interaction):
    if itn.user.id == OWNER_ID:
        synced = await bot.tree.sync()
        await itn.response.send_message(f"📡 Synced {len(synced)} commands!")
    else:
        await itn.response.send_message("❌ Owner only.", ephemeral=True)

# --- 5. STARTUP ---
@bot.event
async def on_ready():
    print(f"🚀 Bot online as {bot.user}")
    try:
        await bot.tree.sync()
        print("📡 Slash commands auto-synced.")
    except Exception as e:
        print(f"❌ Auto-sync failed: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(TOKEN)
