import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from keep_alive import keep_alive

# --- INITIALIZATION ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Options for YouTube/FFmpeg
YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True', 'quiet': True}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="!help | 4-in-1 Bot"))

# --- 1. SMART MODERATION ---
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 5):
        """Purge messages: !clear 10"""
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"🧹 Deleted {amount} messages.", delete_after=3)

# --- 2. MUSIC & PARTY (STAGE SUPPORT) ---
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def play(self, ctx, *, search):
        """Plays from YouTube: !play <url or keywords>"""
        if not ctx.author.voice:
            return await ctx.send("Join a voice/stage channel first!")

        # Join and handle Stage speaker status
        if not ctx.voice_client:
            vc = await ctx.author.voice.channel.connect()
            if isinstance(ctx.author.voice.channel, discord.StageChannel):
                try:
                    await ctx.guild.me.edit(suppress=False)
                except:
                    await ctx.send("⚠️ Manual intervention: Invite me to speak!")
        else:
            vc = ctx.voice_client

        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
                url2 = info['url']
                source = await discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
                vc.play(source)
        await ctx.send(f"🎶 Now Playing: **{info['title']}**")

    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

# --- 3. SKILL BOT (XP SYSTEM) ---
class Skills(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_data = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        uid = str(message.author.id)
        self.xp_data[uid] = self.xp_data.get(uid, 0) + 10

    @commands.command()
    async def rank(self, ctx):
        xp = self.xp_data.get(str(ctx.author.id), 0)
        await ctx.send(f"🏆 {ctx.author.name}, you have **{xp} XP**!")

# --- 4. UTILITY ---
class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send(f"📡 Latency: {round(self.bot.latency * 1000)}ms")

# --- LAUNCH ---
async def main():
    keep_alive() # Start the web server for Render
    async with bot:
        await bot.add_cog(Moderation(bot))
        await bot.add_cog(Music(bot))
        await bot.add_cog(Skills(bot))
        await bot.add_cog(Utility(bot))
        # This looks for your token in Render Environment Variables
        await bot.start(os.getenv('TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())
