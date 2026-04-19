import discord, yt_dlp, os, threading
from discord import app_commands
from discord.ext import commands
from google import genai
from flask import Flask

# --- 1. WEB SERVER (For Render Keep-Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online and Ready!"

def run_web():
    # Render uses port 10000 by default
    app.run(host='0.0.0.0', port=10000)

# --- 2. SMART CONFIG LOADER ---
TOKEN = os.getenv('DISCORD_TOKEN')
AI_KEY = os.getenv('GEMINI_KEY')

# If no environment variables, try loading from Windows Desktop
if not TOKEN:
    try:
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        path = os.path.join(desktop, "credentials.txt")
        if os.path.exists(path):
            with open(path, "r") as f:
                lines = f.read().splitlines()
                TOKEN = lines[0].strip()
                AI_KEY = lines[1].strip()
                print("🏠 [LOCAL] Keys loaded from Desktop.")
    except Exception as e:
        print(f"⚠️ [CONFIG] Could not load local credentials: {e}")

# OS Detection for FFmpeg
# 'posix' = Render (Linux) | 'nt' = Your PC (Windows)
if os.name == 'posix':
    FFMPEG_PATH = "ffmpeg"
else:
    FFMPEG_PATH = "C:/Users/batik/Desktop/ffmpeg.exe"

loop_status = {}

# --- 3. BOT CLASS ---
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        print(f"🚀 {self.user} logged in.")
        print(f"💻 System: {'Render/Linux' if os.name == 'posix' else 'Windows PC'}")

bot = MyBot()
ai_client = genai.Client(api_key=AI_KEY) if AI_KEY else None

# --- 4. MUSIC ENGINE ---
def play_next(vc, guild_id, info):
    if loop_status.get(guild_id, False) and vc.is_connected():
        source = discord.FFmpegOpusAudio(info['url'], executable=FFMPEG_PATH, 
            before_options="-reconnect 1 -reconnect_streamed 1", options="-vn")
        vc.play(source, after=lambda e: play_next(vc, guild_id, info))

@bot.tree.command(name="play", description="Search & Play music with optional Loop")
async def play(itn: discord.Interaction, search: str, filter_author: str = None, looped: bool = False):
    await itn.response.defer()
    if not itn.user.voice: return await itn.followup.send("❌ Join a VC first!")
    
    guild_id = itn.guild.id
    loop_status[guild_id] = looped
    vc = itn.guild.voice_client or await itn.user.voice.channel.connect()

    with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'quiet': True}) as ydl:
        try:
            # Search 5 results
            info = ydl.extract_info(f"ytsearch5:{search}", download=False)
            entries = info.get('entries', [])
            if filter_author:
                entries = [e for e in entries if filter_author.lower() in e.get('uploader', '').lower()]
            
            if not entries: return await itn.followup.send("❌ No matches found.")
            target = ydl.extract_info(entries[0]['url'], download=False)
            
            source = discord.FFmpegOpusAudio(target['url'], executable=FFMPEG_PATH, 
                                             before_options="-reconnect 1 -reconnect_streamed 1", options="-vn")
            
            if vc.is_playing(): vc.stop()
            vc.play(source, after=lambda e: play_next(vc, guild_id, target))
            
            # Handle Stage topic
            if isinstance(itn.user.voice.channel, discord.StageChannel):
                await itn.guild.me.edit(suppress=False)
                if not itn.user.voice.channel.instance:
                    await itn.user.voice.channel.create_instance(topic=f"🎶 {target['title'][:80]}")

            await itn.followup.send(f"✅ **{'Looping' if looped else 'Playing'}**: {target['title']}\n🔗 {target.get('webpage_url')}")
        except Exception as e: await itn.followup.send(f"⚠️ Play Error: {e}")

@bot.tree.command(name="load", description="Play a direct URL link")
async def load(itn: discord.Interaction, link: str, looped: bool = False):
    await itn.response.defer()
    if not itn.user.voice: return await itn.followup.send("❌ Join VC!")
    
    loop_status[itn.guild.id] = looped
    vc = itn.guild.voice_client or await itn.user.voice.channel.connect()

    with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'quiet': True}) as ydl:
        try:
            target = ydl.extract_info(link, download=False)
            source = discord.FFmpegOpusAudio(target['url'], executable=FFMPEG_PATH, 
                                             before_options="-reconnect 1 -reconnect_streamed 1", options="-vn")
            if vc.is_playing(): vc.stop()
            vc.play(source, after=lambda e: play_next(vc, itn.guild.id, target))
            await itn.followup.send(f"✅ **Loaded**: {target['title']}\n🔗 {link}")
        except Exception as e: await itn.followup.send(f"⚠️ Link Error: {e}")

# --- 5. AI & UTILITY ---
@bot.tree.command(name="ask", description="Talk to Gemini AI")
async def ask(itn: discord.Interaction, question: str):
    await itn.response.defer()
    res = ai_client.models.generate_content(model="gemini-1.5-flash", contents=question)
    await itn.followup.send(f"🤖 **Gemini:** {res.text[:1900]}")

@bot.tree.command(name="serverinfo", description="Server stats")
async def serverinfo(itn: discord.Interaction):
    g = itn.guild
    e = discord.Embed(title=f"📊 {g.name}", color=0x3498db)
    e.add_field(name="Members", value=g.member_count)
    if g.icon: e.set_thumbnail(url=g.icon.url)
    await itn.response.send_message(embed=e)

@bot.tree.command(name="stop", description="Stop music and clear loop")
async def stop(itn: discord.Interaction):
    if itn.guild.voice_client:
        loop_status[itn.guild.id] = False
        await itn.guild.voice_client.disconnect()
        await itn.response.send_message("⏹️ Disconnected.")
    else: await itn.response.send_message("❌ Not in VC.")

@bot.command()
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send(f"📡 Synced {len(bot.tree.get_commands())} slash commands!")

# --- 6. RUN ---
if __name__ == "__main__":
    # Start Web Thread for Render
    threading.Thread(target=run_web, daemon=True).start()
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ CRITICAL: No Token found in Variables or Desktop!")
