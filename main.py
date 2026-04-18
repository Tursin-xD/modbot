import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import os
from google import genai
from flask import Flask
from threading import Thread

# --- 1. RENDER STAY-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online and Stable!"

def run():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. AI SETUP (NEW SDK) ---
client = genai.Client(api_key="AIzaSyD-q8mzC189sb-2yvIwiSzmB7k0E6WDkmo")

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"🚀 {self.user} is fully synced and ready!")

bot = MyBot()

# --- 3. MODERATION MODULE ---
@bot.tree.command(name="clear", description="Bulk delete messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Swept away {len(deleted)} messages.")

@bot.tree.command(name="kick", description="Kick a troublesome member")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "None"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👞 Kicked {member.display_name}")

# --- 4. PARTY & VIDEO MODULE ---
@bot.tree.command(name="play", description="Play music + Stage Auto-Start")
async def play(interaction: discord.Interaction, search: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Join a channel first!", ephemeral=True)
    
    await interaction.response.defer()
    channel = interaction.user.voice.channel
    vc = interaction.guild.voice_client or await channel.connect()

    ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
        source = discord.FFmpegOpusAudio(info['url'], before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", options="-vn")
        
        # Stage Channel Support
        if isinstance(channel, discord.StageChannel):
            try: await interaction.guild.me.edit(suppress=False)
            except: pass
            if not channel.instance: await channel.create_instance(topic=f"🎶 {info['title'][:90]}")

        if vc.is_playing(): vc.stop()
        vc.play(source)
        await interaction.followup.send(f"🎶 **Now Jamming:** {info['title']}")

@bot.tree.command(name="show", description="Launch YouTube Watch Together")
async def show(interaction: discord.Interaction):
    if not interaction.user.voice: return await interaction.response.send_message("❌ Join VC first!")
    try:
        invite = await interaction.user.voice.channel.create_invite(
            target_type=discord.InviteTarget.embedded_application,
            target_application_id=880218394199220334
        )
        await interaction.response.send_message(f"🎬 **Watch Together Started:** {invite.url}")
    except: await interaction.response.send_message("❌ Activity failed.")

# --- 5. SKILLS & AI ---
xp_data = {}
@bot.event
async def on_message(message):
    if message.author.bot: return
    uid = str(message.author.id)
    xp_data[uid] = xp_data.get(uid, 0) + 10
    await bot.process_commands(message)

@bot.tree.command(name="rank", description="Check your level")
async def rank(interaction: discord.Interaction):
    xp = xp_data.get(str(interaction.user.id), 0)
    await interaction.response.send_message(f"🏆 {interaction.user.name}: Level {xp // 100} ({xp} XP)")

@bot.tree.command(name="ask", description="Talk to Gemini AI")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=question)
        await interaction.followup.send(f"🤖 **Gemini:** {response.text[:1900]}")
    except Exception as e: await interaction.followup.send(f"❌ AI Error: {e}")

# --- 6. UTILITY ---
@bot.tree.command(name="serverinfo", description="View server stats")
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=f"📊 {g.name} Stats", color=discord.Color.blue())
    embed.add_field(name="Members", value=g.member_count)
    embed.add_field(name="Created", value=g.created_at.strftime("%b %d, %Y"))
    if g.icon: embed.set_thumbnail(url=g.icon.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Check bot speed")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"📡 {round(bot.latency * 1000)}ms")

# --- 7. RUN ---
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("🚨 CRITICAL: DISCORD_TOKEN is missing in Render Environment Variables!")
