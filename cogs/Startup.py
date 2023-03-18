from discord.ext import commands
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from lib.db import db

import discord
import os


load_dotenv()
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
SOLO_CHANNEL_ID = int(os.getenv("SOLO_CHANNEL_ID"))

class Startup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    scheduler = AsyncIOScheduler()
    db.autosave(scheduler)


    async def checksolo(self):
        solo = db.records("SELECT * FROM solo")
        if len(solo) != 0:
            for x in solo:
                time_now = datetime.utcnow()
                try:
                    time_in_solo = datetime.strptime(x[3], "%d-%m-%Y")
                except:
                    await self.bot.get_channel(LOG_CHANNEL_ID).send(f"Error revoking solo validation for {x[1]}. Check if you entered end time correctly. Revoke solo validation manually and follow correct format when issuing solo validation next time.")
                else:
                    diff = time_in_solo - time_now
                    if diff.total_seconds() / 60 <= 0:
                        db.execute("DELETE FROM solo WHERE cid = ? AND end_time = ?", x[1], x[3])
                        await self.bot.get_channel(SOLO_CHANNEL_ID).send(f"Solo validation was revoked for {x[1]} as it expired.")


    @commands.Cog.listener()
    async def on_connect(self):
        self.bot.launch_time = datetime.utcnow()
        print("Bot connected!")

    @commands.Cog.listener()
    async def on_ready(self):
        activity = discord.Activity(name="Saudi Arabia vACC Discord 👀 | Developed by Mufassil Yasir | v1.1", type=discord.ActivityType.watching)
        await self.bot.change_presence(activity=activity)
        print ("Starting up")
        channel = self.bot.get_channel(LOG_CHANNEL_ID)
        #await channel.send("Getting Ready..... Engines Started! :man_running: ")
        self.scheduler.start()
        self.scheduler.add_job(self.checksolo, CronTrigger(minute=30))
    
    @commands.command(description = "This command gets you the bot it self statistics. Run the command `!botinfo` and try it out!")
    @commands.guild_only()
    async def uptime(self, ctx):
        embed = discord.Embed(title = "My Statistics:", colour = discord.Color.from_rgb(252, 165, 3), timestamp = datetime.utcnow())
        embed.set_thumbnail(url = self.bot.user.avatar_url)

        delta_uptime = datetime.utcnow() - self.bot.launch_time
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        fields = [("Bot version:", "v1.1", True),
                   ( "Uptime:", f"{days}d, {hours}h, {minutes}m, {seconds}s", True)]
        
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Startup(bot))