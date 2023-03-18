import discord
import os
from dotenv import load_dotenv
from discord.ext import commands


client = discord.Client()
bot = commands.Bot(command_prefix='!', case_insensitive=True, intents = discord.Intents.all())


for filename in os.listdir("./cogs"):
  if filename.endswith(".py") and filename != "__init__.py":
    bot.load_extension(f'cogs.{filename[:-3]}')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)