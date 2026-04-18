import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import os
import google.generativeai as genai
from flask import Flask
from threading import Thread

# --- 1. RENDER WEB SERVER (To stay 24/7) ---
app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
    # Render's default port is 10000
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. AI SETUP ---
genai.configure(api_key="AIzaSyD-q8mzC189sb-2yvIwiSzmB7k0E6WDkmo")
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 3. BOT CORE ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        
    async def on_ready(self):
        print(f"✅ Logged in as {self.user}")
        print("🌐 Hosting: Render Cloud")

bot = MyBot()

# Cloud-optimized FFmpeg settings
YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True', 'quiet': True}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# --- 4. MUSIC & WATCH TOGETHER ---
@bot.tree.command(name="play", description="Play music on Render")
async def play(interaction: discord.Interaction, search: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Join a VC first!")

    await interaction.response.defer()
    vc = interaction.guild.voice_client or await interaction.user.voice.channel.connect()

    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
            # On Render, we don't use 'executable=...'. We just use 'ffmpeg'
            source = discord.FFmpegOpusAudio(info['url'], **FFMPEG_OPTIONS)
            
            if vc.is_playing(): vc.stop()
            vc.play(source)
            await interaction.followup.send(f"🎶 Playing: **{info['title']}**")
        except Exception as e:
            await interaction.followup.send(f"⚠️ Error: {e}")

@bot.tree.command(name="show", description="Watch Together Activity")
async def show(interaction: discord.Interaction):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Join a VC first!")
    
    # YouTube Activity ID
    try:
        invite = await interaction.user.voice.channel.create_invite(
            target_type=discord.InviteTarget.embedded_application,
            target_application_id=880218394199220334
        )
        await interaction.response.send_message(f"🎬 Click to Watch Together: {invite.url}")
    except:
        await interaction.response.send_message("❌ Activity failed to start.")

# --- 5. AI & UTILITY ---
@bot.tree.command(name="ask", description="Gemini AI")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    response = model.generate_content(question)
    await interaction.followup.send(f"🤖 **Gemini:** {response.text[:1900]}")

@bot.tree.command(name="serverinfo", description="Stats")
async def serverinfo(interaction: discord.Interaction):
    await interaction.response.send_message(f"📊 {interaction.guild.name} | {interaction.guild.member_count} members")

# --- 6. XP SYSTEM ---
xp_data = {}
@bot.event
async def on_message(message):
    if message.author.bot: return
    uid = str(message.author.id)
    xp_data[uid] = xp_data.get(uid, 0) + 10
    await bot.process_commands(message)

# --- RUN ---
if __name__ == "__main__":
    keep_alive() 
    # Important: Set 'DISCORD_TOKEN' in Render Environment Variables
    token = os.getenv("DISCORD_TOKEN") 
    bot.run(token)
