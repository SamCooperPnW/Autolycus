from dotenv import load_dotenv
import pymongo
import os
import pathlib
import discord
import logging
import datetime
import pnwkit
import motor.motor_asyncio
import asyncio
import asyncio
from server import run
from discord.bot import ApplicationCommandMixin
from discord.ext import commands
intents = discord.Intents.default()
intents.members = True
load_dotenv()

# async mongo fuquiem
client = pymongo.MongoClient(os.getenv("pymongolink"))
version = os.getenv("version")
mongo = client[str(version)]
async_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("pymongolink"), serverSelectionTimeoutMS=5000)
async_mongo = async_client[str(version)]

# async mongo autolycus
db_client = pymongo.MongoClient(os.getenv("databaselink"))
db_version = os.getenv("version")
db_async_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("databaselink"), serverSelectionTimeoutMS=5000)
main_async_db = db_async_client["main"]
dependent_async_db = db_async_client[str(db_version)]

# envs
api_key = os.getenv("api_key")
channel_id = int(os.getenv("debug_channel"))

# logger
logging.basicConfig(filename="logs.log", filemode='a', format='%(levelname)s %(asctime)s.%(msecs)d %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)
logger = logging.getLogger()

# pnwkit
kit = pnwkit.QueryKit(api_key)

# discord bot
bot = commands.Bot(intents=intents)

# creating files if they do not exist and reseting them
cwd = pathlib.Path.cwd()
pathlib.Path(f"{cwd}/data/web").mkdir(exist_ok=True)
for directory in ["data/web/builds.json", "data/web/damage.json", "data/web/raids.json", "data/web/attacksheet.json"]:
    with open(f"{cwd}/{directory}", "w+") as f:
        f.write("[]")
pathlib.Path(f"{cwd}/data/nations.json").touch(exist_ok=True)

# cogs
for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')

@bot.event
async def on_ready():
    guilds = sorted(bot.guilds, key=lambda x: x.member_count, reverse=True)
    n = len(guilds)
    logger.info(f"I am in {n} servers:")
    for guild in guilds:
        extra = ""
        try:
            await ApplicationCommandMixin.get_desynced_commands(bot, guild.id)
        except discord.errors.Forbidden:
            owner = guild.owner
            extra = f"|| Slash disallowed, DM {owner}"
            n -= 1
        logger.info(f"-> {guild.member_count} members || {guild} {extra}")
    logger.info(f"Slash commands are allowed in {n}/{len(bot.guilds)} guilds")
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="Orbis"))
    logger.info('We have logged in as {0.user}'.format(bot))

@bot.event
async def on_application_command(ctx: discord.ApplicationContext):
    try:
        channel = {"name": ctx.channel.name, "id": ctx.channel_id}
    except:
        channel = {"name": f"{ctx.author.name}'s DM's", "id": ctx.channel_id}
    try:
        guild = {"name": ctx.guild.name, "id": ctx.guild_id}
    except:
        guild = {"name": f"{ctx.author.name}'s DM's", "id": None}
    await async_mongo.commands.insert_one({"command": ctx.command.name, "time": round(datetime.datetime.utcnow().timestamp()), "user": {"name": ctx.author.name, "id": ctx.author.id}, "channel": channel, "guild": guild})

@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error):
    debug_channel = bot.get_channel(channel_id)
    logger.error(error)
    print(error)
    print(type(error))
    if "MissingPermissions" in str(error):
        await ctx.respond(error.original)
    elif "NoPrivateMessage" in str(error) or isinstance(error, commands.errors.NoPrivateMessage):
        await ctx.respond(error.original)
    elif "ValueError" in str(error) and "cost" in str(ctx.command):
        await ctx.respond(error.original)
    elif "Unknown interaction" in str(error):
        await ctx.respond(f"My bad <@{ctx.author.id}>! Discord claims I didn't respond fast enough, please try that again!")
        await debug_channel.send(f'**Exception caught!**\nAuthor: {ctx.author}\nServer: {ctx.guild}\nCommand: {ctx.command}\nType: {type(error)}\n\nError:```{error}```')
    elif isinstance(error, (discord.HTTPException, discord.errors.NotFound)):
        await debug_channel.send(f'**Exception __caught__!**\nAuthor: {ctx.author}\nServer: {ctx.guild}\nCommand: {ctx.command}\nType: {type(error)}\n\nError:```{error}```')
    else:
        await ctx.send("Oh no! An unknown error occurred! Contact RandomNoobster#0093, and he might be able to help you out.")
        await debug_channel.send(f'**Exception raised!**\nAuthor: {ctx.author}\nServer: {ctx.guild}\nCommand: {ctx.command}\nType: {type(error)}\n\nError:```{error}```'[:2000])

@bot.slash_command(name="ping", description="Pong!")
async def ping(ctx: discord.ApplicationContext):
    await ctx.respond(f'Pong! {round(bot.latency * 1000)}ms')

asyncio.ensure_future(run())
bot.run(os.getenv("bot_token"))