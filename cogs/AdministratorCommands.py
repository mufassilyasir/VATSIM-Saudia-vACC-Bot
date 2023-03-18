from discord.ext import commands
from lib.db import db

import traceback
import os
import asyncio

class AdministratorCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_any_role(869528318003777617, 869528317987012671, 922461285520650293)
    async def addsolo(self, ctx):
        name_ask = await ctx.send(f"Hi {ctx.message.author.display_name}, what is the student name? (Name only without ID please), reply within 30 seconds.")

        try:
            name_ask_wait = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout = 30.0)

        except asyncio.TimeoutError:
            await name_ask.delete()
            await ctx.send("Time is up.")
        
        else:
            cid_ask = await ctx.send("Now the person's CID only. Reply within 30 seconds.")

            try:
                cid_ask_wait = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout = 30.0)
                try:
                    int(cid_ask_wait.content)
                except:
                    await ctx.send("ID must be a number... :pray:")
                    Id = False
                else:
                    Id = True

            except asyncio.TimeoutError:
                await name_ask.delete()
                await name_ask_wait.delete()
                await cid_ask.delete()
                await ctx.send("Time is up.")
                    
            else:

                valid_on_all = await ctx.send("Alright, do you want the person to be solo validated on all airports in the vACC (Y) or only limited airport (N)? Reply within 30 seconds with Y or N.")
                try:
                    valid_on_all_wait = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout = 30.0)
                    valid_on_all_wait = valid_on_all_wait.content.upper()
                except asyncio.TimeoutError:
                    await name_ask.delete()
                    await name_ask_wait.delete()
                    await cid_ask.delete()
                    await valid_on_all.delete()
                    await ctx.send("Time is up.")

                else:
                    if valid_on_all_wait == "Y":
                        valid_all_given = True
                        valid_all = "True"
                    elif valid_on_all_wait == "N":
                        valid_all_given = True
                        valid_all = "False"
                    else:
                        valid_all_given = False

                    if valid_all_given == True:    
                        if Id == True:
                            pos_ask = await ctx.send("Now the person's position to be solo validated on. Reply within 30 seconds.")

                            try:
                                pos_ask_wait = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout = 30.0)
                            
                            except asyncio.TimeoutError:
                                await name_ask.delete()
                                await name_ask_wait.delete()
                                await cid_ask.delete()
                                await pos_ask.delete()
                                await valid_on_all.delete()
                                await valid_on_all_wait.delete()
                                await ctx.send("Time is up.")
                            
                            else:
                                
                                end_time_ask = await ctx.send("When does the solo validation end? Add the date. Format: 'DD-MM-YYYY'. Reply within 30 seconds.")

                                try:
                                    end_time_ask_wait = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout = 30.0)

                                except asyncio.TimeoutError:
                                    await name_ask.delete()
                                    await name_ask_wait.delete()
                                    await cid_ask.delete()
                                    await pos_ask.delete()
                                    await pos_ask_wait.delete()
                                    await end_time_ask.delete()
                                    await valid_on_all.delete()
                                    await valid_on_all_wait.delete()
                                    await ctx.send("Time is up.")

                                else:
                                    db.execute("INSERT INTO solo (cid, position, end_time, name, valid_all) VALUES (?,?,?,?,?)", cid_ask_wait.content, pos_ask_wait.content, end_time_ask_wait.content, name_ask_wait.content, valid_all)
                                    await name_ask.delete()
                                    await name_ask_wait.delete()
                                    await cid_ask.delete()
                                    await pos_ask.delete()
                                    await pos_ask_wait.delete()
                                    await end_time_ask.delete()
                                    await valid_on_all.delete()
                                    await valid_on_all_wait.delete()
                                    await end_time_ask_wait.delete()
                                    await ctx.send(f"Solo validation issued for {cid_ask_wait.content}")
                        else:       
                            pass
                    
                    else:
                        await name_ask.delete()
                        await name_ask_wait.delete()
                        await cid_ask.delete()
                        await valid_on_all.delete()
                        await valid_on_all_wait.delete()
                        await ctx.send("Answer must be Y or N only.")

    @commands.command()
    @commands.has_any_role(869528318003777617, 869528317987012671, 922461285520650293)
    async def revokesolo(self, ctx):
        await ctx.trigger_typing()
        cid_ask = await ctx.send("What's the CID of the member you wish to revoke solo for? Reply within 30 seconds.")
        
        try:
            cid_ask_wait = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout = 30.0)

        except asyncio.TimeoutError:
            await cid_ask.delete()
            await ctx.send("Oops, you timed out!")
        
        else:
            try:
                int(cid_ask_wait.content)
            except:
                await ctx.send("Are you sure that is a real VATSIM ID? :thinking:")
            else:
                pos_ask = await ctx.send("What's the position of the member you wish to revoke solo for? Reply within 30 seconds.")
                
                try:
                    pos_ask_wait = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout = 30.0)
                except asyncio.TimeoutError:
                    await cid_ask.delete()
                    await cid_ask_wait.delete()
                    await pos_ask.delete()
                    await ctx.send("Oops, you timed out!")
                else:
                
                    cid = db.field("SELECT cid FROM solo WHERE ( cid = ? AND position = ? )", cid_ask_wait.content, pos_ask_wait.content)
                    if cid != None:
                        try:
                            db.execute("DELETE FROM solo WHERE ( cid = ? AND position = ? )", cid_ask_wait.content, pos_ask_wait.content)
                        except:
                            await ctx.send("There was an issue revoking the solo. If the issue persists, please contact Ismail.")
                        else:
                            await ctx.send(f"Solo Validation for {cid_ask_wait.content} was revoked. :white_check_mark: ")
                    else:
                        await ctx.send("Ah oh, I don't think there was any solo validation issued for that CID. Please check again.")
        
    
    
    @commands.command()
    @commands.is_owner()
    async def reload_cog(self, ctx, cog: str):
        await ctx.trigger_typing()
        ext = f"{cog}.py"
        if not os.path.exists(f"./cogs/{ext}"):
            await ctx.send(f"{ctx.message.author.display_name} I could not unload that Cog. Possibly spelling issue...")
        elif ext.endswith(".py") and not ext.startswith("_"):
            try:
                self.bot.unload_extension(f"cogs.{ext[:-3]}")
                self.bot.load_extension(f"cogs.{ext[:-3]}")
            except Exception:
                desired_trace = traceback.format_exc()
                await ctx.send(f"Failed to reload Cog: `{ext}`\nTrackback Error:\n{desired_trace}")
            else:
                await ctx.send(f"Successfully reloaded Cog {cog}")
    
    @commands.command()
    @commands.is_owner()
    async def load_cog(self, ctx, cog: str):
        await ctx.trigger_typing()
        ext = f"{cog}.py"
        if not os.path.exists(f"./cogs/{ext}"):
            await ctx.send(f"{ctx.message.author.display_name} I could not load Cog {cog}. Possibly spelling issue...")
        
        elif ext.endswith(".py") and not ext.startswith("_"):
            try:
                self.bot.load_extension(f"cogs.{ext[:-3]}")
            except Exception:
                desired_trace = traceback.format_exc()
                await ctx.send(f"Failed to log Cog: `{ext}`\nTrackback Error:\n{desired_trace}")
            else:
                await ctx.send(f"Successfully reloaded Cog {cog}")



def setup(bot):
    bot.add_cog(AdministratorCommands(bot))