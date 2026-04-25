import discord, yt_dlp, os, threading, asyncio
from discord import app_commands
from discord.ext import commands
from google import genai
from flask import Flask

# --- 1. THE RAILWAY "BUG" FIX ---
# This manually tells Python to look in every possible Linux folder for FFmpeg
os.environ["PATH"] += os.pathsep + "/usr/bin" + os.pathsep + "/usr/local/bin" + os.pathsep + "/bin"

app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. CONFIG ---
OWNER_ID = 1459506686157914213
TOKEN = os.getenv('DISCORD_TOKEN')
AI_KEY = os.getenv('GEMINI_KEY')

# Using the exact data from your original JSON file
COOKIE_DATA = "76Hn7ETcaPWaQl75bIeEesaVvG2Rlfbibo2VMYt3YhEXbRam1UoHzU050zSC0F/Yju8CcQTjvs6W42uYnUZOzTy+n6EPh3GvCbpub2zWsuVPoaLambYFQ3yFZ4alyGysdn7PqM8dE3U3ubJVBAPrCi+EvoV1dqlpxZoNDS3opjXKuCqstWhp6sxNrmxwrjjz3CyZtR4HRrFqcLXAd47lkb3c34vaQPVM80NQa1PIyi/cEgBNQySAA/gKRVYyjLH96LUg7REt5rNs52txi8Tb7Mg+66T4YZ0Qly4JVKmMql/91J6p7gqLZDXpGm2uEppBabfa+nIE0m/L91mZuhrKSW+4yf6JEU+tZlQogkHWD+DZr1ic1idUHic4Aq0MGezhfIob1QgT1zPB38p6SFiKsoO4ncqXDCN6/1Fslei+lTsAZ01XTfopDbEyXzx0f3H933NbFC9zrCJH0TuW6sV96auUBo/J+e5rFwj6OA/615..."

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
            'cookiefile': 'cookies.txt',
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'mweb'],
                }
            },
            # Add a real User-Agent so YouTube doesn't think you're a bot script
            #restart here
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'ignoreerrors': True,
        }
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            # We add a small retry logic for the search
            try:
                search_query = query if is_url else f"ytsearch1:{query}"
                print(f"DEBUG: Searching for {search_query}") # Check your Railway logs for this!
                
                info = ydl.extract_info(search_query, download=False)
                
                if info and 'entries' in info and len(info['entries']) > 0:
                    return info['entries'][0]
                return info 
            except Exception as e:
                print(f"DEBUG SEARCH ERROR: {e}")
                return None
                
    return await loop.run_in_executor(None, fetch)

@bot.tree.command(name="play", description="Play music")
async def play(itn: discord.Interaction, search: str):
    await itn.response.defer()
    
    # 1. Get song data
    song_data = await get_info(search, is_url=search.startswith("http"))
    
    # 2. Check if search actually worked
    if not song_data:
        return await itn.followup.send("❌ Error: Could not find song or YouTube is blocking the request.")

    # 3. Connect to voice
    if not itn.user.voice:
        return await itn.followup.send("Join a voice channel first!")
        
    vc = itn.guild.voice_client or await itn.user.voice.channel.connect()
    
    if vc.is_playing():
        vc.stop()

    # 4. Play the music
    try:
        # 'ffmpeg' works if NIXPACKS_PKGS is set to include ffmpeg
        source = await discord.FFmpegOpusAudio.from_probe(song_data['url'], method='fallback')
        vc.play(source)
        await itn.followup.send(f"🎶 Now playing: **{song_data.get('title', 'Unknown Title')}**")
    except Exception as e:
        await itn.followup.send(f"❌ FFmpeg Error: {e}")
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
    await itn.response.send_message(f"👤 {m.name} | ID: {m.id}")

@bot.tree.command(name="show", description="Watch Together")
async def show(itn: discord.Interaction):
    if not itn.user.voice: return await itn.response.send_message("Join VC!")
    inv = await itn.user.voice.channel.create_invite(target_type=discord.InviteTarget.embedded_application, target_application_id=880218394199220334)
    await itn.response.send_message(f"🎬 {inv.url}")

@bot.tree.command(name="sync", description="Sync commands")
async def sync_cmd(itn: discord.Interaction):
    if itn.user.id == OWNER_ID:
        synced = await bot.tree.sync()
        await itn.response.send_message(f"📡 Synced {len(synced)} commands!")

# --- 5. STARTUP ---
@bot.event
async def on_ready():
    print(f"🚀 Bot online as {bot.user}")
    await bot.tree.sync()

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(TOKEN)
