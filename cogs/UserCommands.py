from discord.ext import commands
from time import time
from discord.ext.commands.errors import MissingRequiredArgument
from dotenv import load_dotenv
from lib.db import db
from math import radians, cos, sin, sqrt, atan2
from datetime import datetime, timedelta

import aiohttp
import discord
import os
import requests
import time

load_dotenv()
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #Ping command
    @commands.command(description = "This command calculates the time taken from the message being sent by the user and the message being returned by the bot. Use `!ping` and you will get a ping. ", brief = "Displays time taken by the server to respond back in ms")
    @commands.guild_only()
    async def Ping(self, ctx):
        start = time.time()
        message = await ctx.send("Pinging Server...")
        end = time.time()

        await message.edit(content = f"Server to Discord latency: `{self.bot.latency*1000:,.0f}` ms\nUser to bot response time `{(end-start)*1000:,.0f}` ms. :fire:")

    
   #metar API
    @commands.command(description = "This command displays metar for the specified ICAO code. Use `!metar` followed by the ICAO code and you will be displayed the METAR information for that airport.", brief = "Displays metar for the specified ICAO")
    @commands.guild_only()
    async def Metar(self, ctx,*,icao_random :str):
        icao = icao_random.upper()
        url = f"https://api.checkwx.com/metar/{icao}/decoded"

        async with ctx.channel.typing():
            async with aiohttp.ClientSession() as cs:
                headers = {"X-API-Key": "13b7b59ea5404c29bd637e3a5f"}
                async with cs.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data["results"] == 1:
                            data_original = str(data["data"][0]['raw_text'])


                            embed = discord.Embed(title = "Metar Information", colour = discord.Color.from_rgb(252, 165, 3))
                            embed.add_field(inline=False, name=f"{icao} Metar:", value=data_original)
                            await ctx.send(embed=embed)

                    
                        else:
                            await ctx.send(f"Oops {ctx.message.author.display_name}, that ICAO was not found. Are you sure that ICAO code matches an airport ICAO? :face_with_raised_eyebrow: `Err: InvalidICAOCode` ")

                    elif response.status == 401:
                        await ctx.send("This doesn't happen often, standby. `Err:Invalidcred`")
                    
                    elif response.status == 429:
                        await ctx.send("Metar service is down. `Err:Servicenotresponding`")
                
                    elif response.status == 404:
                        await ctx.send(f"Oops {ctx.message.author.display_name}, that ICAO was not found. Are you sure that ICAO code matches an airport ICAO? :face_with_raised_eyebrow: `Err: InvalidICAOCode` ")
                
                    else:
                        await ctx.send(f"`Err: {response.status} response code`")
    @Metar.error
    async def Metar_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please enter an icao code after the command for example, `!metar oejn`")

    @commands.command(description = "Displays the active solo validations in the vACC. To run the command use `!solovalidations`")
    @commands.guild_only()
    async def solovalidations(self, ctx):
        solo = db.records("SELECT * FROM solo")
        embed=discord.Embed(title="Saudi Arabia vACC Solo Validations", colour = discord.Color.from_rgb(252, 165, 3))
        count = 0
        if len(solo) != 0:
            for x in solo:
                count += 1
                embed.add_field(inline=False, name=f"**{count}**. {x[4]} - {x[1]}", value=f"Solo Validated on {x[2]} till {x[3]}")
        else:
            embed.add_field(inline=False, name="No solo validations issued.", value="\u200b")
        await ctx.send(embed=embed)
        

    # @commands.command()
    # @commands.guild_only()
    # async def requestatc(self, ctx):
    #     airport_ask = await ctx.send("Hi, what will be the airport ICAO code in which you are requesting ATC? Reply within 25 seconds.")

    #     try:
    #         airport_ask_wait = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout = 25.0)

    #     except asyncio.TimeoutError:
    #         await airport_ask.delete()
    #         await ctx.send("Time is up.")
        
    #     else:
    #         time_ask = await ctx.send("What will be the UTC time when you require ATC services? Format example: '25th December, 2021 at 1300z' Reply within 30 seconds.")


    #         try:
    #             time_ask_wait = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout = 30.0)

    #         except asyncio.TimeoutError:
    #             await airport_ask.delete()
    #             await airport_ask_wait.delete()
    #             await time_ask.delete()
    #             await ctx.send("Time is up.")
        
    #         else:
    #             #send to controller room
    #             embed = discord.Embed(title="ATC Services Requested", colour = discord.Color.from_rgb(252, 165, 3))
    #             embed.add_field(inline=False, name="Airport ICAO", value=airport_ask_wait.content)
    #             embed.add_field(inline=False, name="Time (UTC)", value=time_ask_wait.content)
    #             embed.set_footer(text=f"Requested by {ctx.message.author.name}", icon_url=ctx.author.avatar_url)
    #             controller_channel = self.bot.get_channel(923105821796225024)
    #             await controller_channel.send(embed=embed)
    #             await ctx.send("ATC services requested. Kindly be patient a controller will reply to you as soon as possible.")
    #             await airport_ask.delete()
    #             await airport_ask_wait.delete()
    #             await time_ask.delete()
    #             await time_ask_wait.delete()
    
    @commands.command(description = "Displays metar, active runway (for OEJN, OEDF, OERK for now), number of departures, number of arrivals and Online ATC for the vACC. An example to run the command is `!info oejn` ")
    @commands.guild_only()
    async def info(self, ctx, icao :str):
        loading_embed = discord.Embed(colour = discord.Color.from_rgb(252, 165, 3))
        loading_embed.set_author(name=f"Standby {ctx.message.author.display_name}, this is gonna take some time.", icon_url="https://media.giphy.com/media/sSgvbe1m3n93G/source.gif?cid=ecf05e47a0z65sl6qyqji8f06i3zanuj9s581zjo8pp2jns9&rid=source.gif&ct=g")
        msg = await ctx.send(embed=loading_embed)
        url = f"https://api.checkwx.com/metar/{icao.upper()}/decoded"
        is_an_airport = True

        async with aiohttp.ClientSession() as cs:
            headers = {"X-API-Key": "13b7b59ea5404c29bd637e3a5f"}
            async with cs.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    if data["results"] == 1:
                        data_original = str(data["data"][0]['raw_text'])
                        if icao.upper() == "OEJN":
                            if int(data['data'][0]['wind']['speed_kts']) < 6:
                                runway = 34
                            elif int(data['data'][0]['wind']['degrees']) >= 250 and int(data['data'][0]['wind']['degrees']) <= 359:
                                runway = 34
                            elif int(data['data'][0]['wind']['degrees']) >= 000 and int(data['data'][0]['wind']['degrees']) <= 70:
                                runway = 34
                            elif int(data['data'][0]['wind']['degrees']) >= 80 and int(data['data'][0]['wind']['degrees']) <= 240:
                                runway = 16
                            else:
                                runway = "N//A"

                        elif icao.upper() == "OEDF":
                            if int(data['data'][0]['wind']['speed_kts']) < 6:
                                runway = 34
                            elif int(data['data'][0]['wind']['degrees']) >= 250 and int(data['data'][0]['wind']['degrees']) <= 359:
                                runway = 34
                            elif int(data['data'][0]['wind']['degrees']) >= 000 and int(data['data'][0]['wind']['degrees']) <= 70:
                                runway = 34
                            elif int(data['data'][0]['wind']['degrees']) >= 80 and int(data['data'][0]['wind']['degrees']) <= 240:
                                runway = 16
                            else:
                                runway = "N//A"
                        
                        elif icao.upper() == "OERK":
                            if int(data['data'][0]['wind']['speed_kts']) < 6:
                                runway = 33
                            elif int(data['data'][0]['wind']['degrees']) >= 240 and int(data['data'][0]['wind']['degrees']) <= 359:
                                runway = 33
                            elif int(data['data'][0]['wind']['degrees']) >= 000 and int(data['data'][0]['wind']['degrees']) <= 60:
                                runway = 33
                            elif int(data['data'][0]['wind']['degrees']) >= 70 and int(data['data'][0]['wind']['degrees']) <= 230:
                                runway = 15
                            else:
                                runway = "N//A"

                    else:
                        data_original = "ICAO Not Found"
                        is_an_airport = False
                        print(f"Oops {ctx.message.author.display_name}, that ICAO was not found. Are you sure that ICAO code matches an airport ICAO? :face_with_raised_eyebrow: `Err: InvalidICAOCode` ")

                elif response.status == 401:
                    data_original = "N/A"
                    print("This doesn't happen often, standby. `Err:Invalidcred`")
                
                elif response.status == 429:
                    data_original = "N/A"
                    print("Metar service is down. `Err:Servicenotresponding`")
            
                elif response.status == 404:
                    data_original = "N/A"
                    is_an_airport = False
                    print(f"Oops {ctx.message.author.display_name}, that ICAO was not found. Are you sure that ICAO code matches an airport ICAO? :face_with_raised_eyebrow: `Err: InvalidICAOCode` ")
            
                else:
                    data_original = "N/A"
                    print(f"`Err: {response.status} response code`")
        
        if is_an_airport == True:
        
            r = requests.get("https://data.vatsim.net/v3/vatsim-data.json")
            if r.status_code == 200:
                try:
                    data1 = r.json()
                except:
                    dep_count = "N/A"
                    arr_count = "N/A"
                else:
                    dep_count = 0
                    arr_count = 0
                    for x in data1['pilots']:
                        if x['callsign'] == "AUI391":
                            print(x)
                        if x['flight_plan'] != None:
                            if x['flight_plan']['departure'] != None:
                                if x['flight_plan']['departure'] == icao.upper():
                                    dep_count += 1
                            if x['flight_plan']['arrival'] != None:
                                if x['flight_plan']['arrival'] == icao.upper():
                                    arr_count += 1

            embed = discord.Embed(title=f"{icao.upper()} Airport Information", colour = discord.Color.from_rgb(252, 165, 3))
            embed.add_field(inline=False, name=f"{icao.upper()} Metar", value=data_original)
            if icao.upper() == "OEJN" or icao.upper() == "OEDF" or icao.upper() == "OERK":
                embed.add_field(inline=False, name=f"{icao.upper()} Active Runway", value=runway)
            embed.add_field(inline=False, name=f"{icao.upper()} Departures", value=dep_count)
            embed.add_field(inline=False, name=f"{icao.upper()} Arrivals", value=arr_count)
            await ctx.send(embed=embed)

            if icao.upper().startswith("OE") and len(icao) == 4 and icao != None:
                online_pos = db.records("SELECT * FROM onlineatc")
                if len(online_pos) != 0:
                    embed2 = discord.Embed(title=f"vACC Online ATC", colour = discord.Color.from_rgb(252, 165, 3))
                    for x in online_pos:
                        embed2.add_field(inline=False, name=x[1], value=f"Controller: {x[4]} - {x[5]}")
                    await ctx.send(embed=embed2)
            
            await msg.delete()

        else:
            await msg.delete()
            await ctx.send(f"Oops {ctx.message.author.display_name}, that ICAO was not found. Are you sure that ICAO code matches an airport ICAO? 🤨 Err: InvalidICAOCode")
    
    @info.error
    async def info_error(self, ctx, error):        
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("Please mention the airport icao code. Example: !info oejn")

    @commands.command(description = "Displays Online ATC for the entire vACC. To run this command use `onlineatc`")
    @commands.guild_only()
    async def onlineatc(self, ctx):
        embed = discord.Embed(title=f"Online ATC", colour = discord.Color.from_rgb(252, 165, 3))
        online = db.records("SELECT * FROM onlineatc")
        solo = db.records("SELECT * FROM solo")
        is_solo = ""

        if len(online) != 0:
            for x in online:
                for s in solo:
                    if int(s[1]) == int(x[5]):
                        if x[1] == s[2]:
                            is_solo = f"Controller is solo validated on this position till {s[3]}"
                        elif x[1] != s[2]:
                            try:
                                a=x[1].split('_')
                                facility_new = f"{a[0]}_{a[2]}"
                            except:
                                pass
                            else:
                                if s[2] == facility_new:
                                    is_solo = f"Controller is solo validated on this position till {s[3]}"
                
                then = datetime.strptime(x[2][:-2], "%Y-%m-%dT%H:%M:%S.%f")
                diff = datetime.utcnow() - then
                logon_time = time.strftime("%H:%M:%S", time.gmtime(diff.total_seconds()))

                embed.add_field(inline=False, name=x[1], value=f"{x[4]} - {x[5]}. Time online {logon_time}. {is_solo}")
        else:
            embed.add_field(inline=False, name="No ATC online yet.", value="\u200b")
        await ctx.send(embed=embed)
    
    @commands.command(description = "Displays number of arrivals, their callsign, departure airport and ETA to the airport and displays number of departures, their callsign, arrival airport and departure time for the specified airport ICAO code. ")
    @commands.guild_only()
    async def traffic(self, ctx, icao :str):
        if icao.upper().startswith("OE") and len(icao) == 4 and icao != None:
            def distance(lat1, lat2, lon1, lon2):

                lat1 = radians(lat1)
                lon1 = radians(lon1)
                lat2 = radians(lat2)
                lon2 = radians(lon2)

                dlon = lon2 - lon1

                dlat = lat2 - lat1
        
                a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))
                R = 6373.0
                distance = R * c
                return distance


            r = requests.get("https://data.vatsim.net/v3/vatsim-data.json")
            if r.status_code == 200:
                try:
                    data1 = r.json()
                except:
                    dep_count = "N/A"
                    arr_count = "N/A"
                    arrivals = "N/A"
                    departures = "N/A"
                    await ctx.send("Uh oh, it appears VATSIM server could not be reached. Please try again later. :confused:")
                else:
                    dep_count = 0
                    arr_count = 0
                    arrivals = []
                    departures = []
                
                    for x in data1['pilots']:
                        if x['flight_plan'] != None:
                            if x['flight_plan']['departure'] != None:
                                if x['flight_plan']['departure'] == icao.upper():
                                    departures.append(f"[{str(x['callsign'])},{str(x['flight_plan']['arrival'])},{str(x['flight_plan']['deptime'])}]")
                                    dep_count += 1
                            if x['flight_plan']['arrival'] != None:
                                if x['flight_plan']['arrival'] == icao.upper():
                                    arr_count += 1
                                    eta = "N/A"
                                    if icao.upper().startswith("OE"):
                                        dist = distance(float(db.field("SELECT coordinate1 FROM airports WHERE icao = ?", icao.upper())), x['latitude'], float(db.field("SELECT coordinate2 FROM airports WHERE icao = ?", icao.upper())), x['longitude'])
                                        dist_nm = dist / 1.852
                        
                                        if int(x['groundspeed']) != 0:
                                            time1 = dist_nm / x['groundspeed']
                                            time_in_mins = time1 * 60
                                            time_then = datetime.utcnow() + timedelta(minutes=time_in_mins)
                                            eta = datetime.strftime(time_then, "%H:%M")
                                    arrivals.append(f"[{str(x['callsign'])},{str(eta)},{str(x['flight_plan']['departure'])}]")

                    embed = discord.Embed(title=f"{icao.upper()} Arrival Traffic Statistics", colour = discord.Color.from_rgb(252, 165, 3))
                    embed.add_field(inline=False, name=f"Arrivals: {arr_count}", value=f"\u200b")
                    if len(arrivals) != 0:
                        for arr in arrivals:
                            arr =  arr.strip('][').split(', ')
                            embed.add_field(inline=True, name=f"Callsign:", value=f"{arr[0].split(',')[0]}")
                            embed.add_field(inline=True, name=f"Departure:", value=f"{arr[0].split(',')[2]}")
                            embed.add_field(inline=True, name="ETA", value=f"{arr[0].split(',')[1]}Z")

                    embed2 = discord.Embed(title=f"{icao.upper()} Departure Traffic Statistics", colour = discord.Color.from_rgb(252, 165, 3))
                    embed2.add_field(inline=False, name=f"Departures: {dep_count}", value=f"\u200b")

                    if len(departures) != 0:
                        for depx in departures:
                            dep =  depx.strip('][').split(', ')
                            embed2.add_field(inline=True, name=f"Callsign:", value=f"{dep[0].split(',')[0]}")
                            embed2.add_field(inline=True, name=f"Arrival:", value=f"{dep[0].split(',')[1]}")
                            embed2.add_field(inline=True, name=f"Departure Time:", value=f"{dep[0].split(',')[2]}Z")

                    await ctx.send(embed=embed)
                    await ctx.send(embed=embed2)

            
            else:
                await ctx.send("Uh oh, it appears VATSIM server could not be reached. Please try again later. :confused:")
        
        else:
            await ctx.send("This command is limited to Saudi Arabia airports only.")

    @traffic.error
    async def traffic_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("Please mention the airport icao code. Example: !traffic oejn")
            
def setup(bot):
    bot.add_cog(UserCommands(bot))


                    