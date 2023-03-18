from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from lib.db import db
from dotenv import load_dotenv

import discord
import aiohttp
import os
import time

load_dotenv()
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
ONLINE_ATC_CHANNEL_ID = int(os.getenv("ONLINE_ATC_CHANNEL_ID"))

class OnlineATC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    scheduler = AsyncIOScheduler()
    db.autosave(scheduler)


    async def online(self):
        url = "https://data.vatsim.net/v3/vatsim-data.json"
        async with aiohttp.ClientSession() as cs:
            async with cs.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    big_list = []
                    for controllers in data['controllers']:
                        callsign = controllers['callsign']
                        big_list.append(callsign)

                        if callsign.startswith("OE"):
                            Bool = db.field("SELECT Bool FROM onlineatc WHERE CallSign = ?", callsign)
                            
                            if Bool != "True":
                                if controllers['frequency'] != "199.998":
                                    name = controllers['name']

                                    DATA = {
                                    "OEJD_1_CTR": "Jeddah Control",
                                    "OEJD_2_CTR": "Jeddah Control",
                                    "OEJD_3_CTR": "Jeddah Control",
                                    "OEJD_4_CTR": "Jeddah Control",
                                    "OEJD_5_CTR": "Jeddah Control",
                                    "OEJD_6_CTR": "Jeddah Control",
                                    "OEJD_7_CTR": "Jeddah Control",
                                    "OEJD_8_CTR": "Jeddah Control",
                                    "OEJN_1_CTR": "Jeddah Terminal Control",
                                    "OEJN_2_CTR": "Jeddah Terminal Control",
                                    "OERD_1_CTR": "Riyadh Control",
                                    "OERD_2_CTR": "Riyadh Control",
                                    "OERD_3_CTR": "Riyadh Control",
                                    "OERD_4_CTR": "Riyadh Control",
                                    "OERK_1_CTR": "Riyadh Terminal Control",
                                    "OERK_2_CTR": "Riyadh Terminal Control",
                                    "OEAB_APP": "Abha Approach",
                                    "OEAB_L_APP": "Abha Approach",
                                    "OEDF_L_APP": "Dammam Approach",
                                    "OEDR_APP": "Dhahran Approach",
                                    "OEGS_APP": "Gassim Approach",
                                    "OEHL_APP": "Hail Approach",
                                    "OEJN_APP": "Jeddah Approach",
                                    "OEJN_F_APP": "Jeddah Final",
                                    "OEMA_APP": "Madinah Approach",
                                    "OEPS_APP": "Prince Sultan Approach",
                                    "OERK_APP": "Riyadh Approach",
                                    "OERK_L_APP": "Riyadh Approach",
                                    "OETB_APP": "Tabuk Approach",
                                    "OETF_APP": "Taif Approach",
                                    "OEAB_GND": "Abha Ground",
                                    "OEGS_GND": "Gassim Ground",
                                    "OEJN_1_GND": "Jeddah Ground",
                                    "OEJN_2_GND": "Jeddah Ground",
                                    "OEJN_3_GND": "Jeddah Ground",
                                    "OEJN_4_GND": "Jeddah Apron",
                                    "OEJN_5_GND": "Jeddah Apron",
                                    "OEJN_DEL": "Jeddah Clearance",
                                    "OEMA_GND": "Madinah Ground",
                                    "OEDF_1_GND": "Dammam Ground",
                                    "OEDF_2_GND": "Dammam Ground",
                                    "OERK_GND": "King Khaled Ground",
                                    "OERK_DEL": "King Khaled Clearance Delivery",
                                    "OEHL_GND": "Hail Ground",
                                    "OEGN_GND": "Jizan Ground",
                                    "OEJB_GND": "Jubail Ground",
                                    "OEDR_GND": "Dhahran Ground",
                                    "OERY_GND": "Riyadh Ground",
                                    "OETB_GND": "Tabuk Ground",
                                    "OEYN_GND": "Yenbo Ground",
                                    "OEAB_TWR": "Abha Tower",
                                    "OEDF_1_TWR": "Dammam Tower",
                                    "OEDF_2_TWR": "Dammam Tower",
                                    "OEDR_1_TWR": "Dhahran Tower",
                                    "OEDR_2_TWR": "Dhahran Tower",
                                    "OEGN_TWR": "Jizan Tower",
                                    "OEGS_TWR": "Gassim Tower",
                                    "OEHL_TWR": "Hail Tower",
                                    "OEJB_TWR": "Jubail Tower",
                                    "OEMA_TWR": "Madinah Tower",
                                    "OERK_TWR": "King Khaled Tower",
                                    "OERY_TWR": "Riyadh Tower",
                                    "OETB_TWR": "Yenbo Tower",
                                    "OEYN_TWR": "Yenbo Tower",
                                    "OEJN_TWR": "Jeddah Tower",
                                    "OENG_TWR" : "",
                                    }
                                    try:
                                        facility = DATA[callsign]
                                        callsign1 = callsign
                                    except KeyError:
                                        a=callsign.split('_')
                                        try:
                                            facility_new = f"{a[0]}_{a[2]}"
                                        except:
                                            facility = callsign
                                            callsign1 = callsign
                                        else:
                                            try:
                                                facility = DATA[facility_new]
                                            except KeyError:
                                                facility = callsign

                                    solo = db.records("SELECT * FROM solo")
                                    description2 = ""
                                    for x in solo:
                                        if int(x[1]) == int(controllers['cid']):
                                            if x[5] == "False":
                                                if x[2] == callsign1:
                                                    description2 = f"Controller is solo validated on this position till {x[3]}"
                                                elif x[2] != callsign1:
                                                    try:
                                                        a = callsign.split('_')
                                                        facility_new = f"{a[0]}_{a[2]}"
                                                    except:
                                                        pass
                                                    else:
                                                        if x[2] == facility_new:
                                                            description2 = f"Controller is solo validated on this position till {x[3]}"
                                            
                                            elif x[5] == "True":
                                                check_pos = callsign.split('_')
                                                if check_pos[1] == x[2]:
                                                    pos = True
                                                else:
                                                    if check_pos[2] == x[2]:
                                                        pos = True
                                                    else:
                                                        pos = False

                                                if pos == True:
                                                    description2 = f"Controller is solo validated on this position till {x[3]}"
                                                
                                    embed = discord.Embed(title = "ATC Online Notification", description = f"{name} - {controllers['cid']} is online on **{facility}** ({callsign})! {description2}",colour = discord.Color.from_rgb(252, 165, 3),timestamp = datetime.utcnow())
                                    embed.set_footer(text="Saudi Arabia vACC", icon_url=self.bot.user.avatar_url)
                                    online_channel = self.bot.get_channel(ONLINE_ATC_CHANNEL_ID)
                                    await online_channel.send(embed=embed)

                                    # then = datetime.strptime(controllers['logon_time'][:-2], "%Y-%m-%dT%H:%M:%S.%f")
                                    # diff = datetime.utcnow() - then
                                    # logon_time = time.strftime("%H:%M:%S", time.gmtime(diff.total_seconds()))

                                    value = "True"
                                    db.execute("INSERT INTO onlineatc (CallSign, TimeOnline, Bool, controller, cid) VALUES (?,?,?,?,?)", callsign, controllers['logon_time'], value, name, controllers['cid'])

                        
                        if "GULF_FSS" in callsign:
                            Bool = db.field("SELECT Bool FROM onlineatc WHERE CallSign = ?", callsign)

                            if Bool != "True":
                                if controllers['frequency'] != "199.998":

                                    name = controllers['name']
                                    DATA = {"GULF_FSS" : "Gulf Control"}


                                    try:
                                        facility = DATA[callsign]
                                    except KeyError:
                                        a=callsign.split('_')
                                        facility_new = f"{a[0]}_{a[2]}"
                                        try:
                                            facility = DATA[facility_new]
                                        except KeyError:
                                            facility = callsign
                                    embed = discord.Embed(title = "ATC Online Notification", description = f"{name} - {controllers['cid']} is online on **{facility}** ({callsign})!",colour = discord.Color.from_rgb(252, 165, 3),timestamp = datetime.utcnow())
                                    embed.set_footer(text="Saudi Arabia vACC", icon_url=self.bot.user.avatar_url)
                                    online_channel = self.bot.get_channel(ONLINE_ATC_CHANNEL_ID)
                                    await online_channel.send(embed=embed)

                                    #then = datetime.strptime(controllers['logon_time'][:-2], "%Y-%m-%dT%H:%M:%S.%f")
                                    # diff = datetime.utcnow() - then
                                    # logon_time = time.strftime("%H:%M:%S", time.gmtime(diff.total_seconds()))

                                    value = "True"
                                    db.execute("INSERT INTO onlineatc (CallSign, TimeOnline, Bool, controller, cid) VALUES (?,?,?,?,?)", callsign, controllers['logon_time'], value, name, controllers['cid'])

                    
                    
                    
        all = db.records("SELECT * FROM onlineatc")
        for a in all:
            if a[1] not in big_list:
                db.execute("DELETE FROM onlineatc WHERE CallSign = ?", a[1])

 
    @commands.Cog.listener()
    async def on_ready(self):
        print("online atc")
        self.scheduler.start()
        self.scheduler.add_job(self.online, CronTrigger(second="19"))                                


def setup(bot):
    bot.add_cog(OnlineATC(bot))
