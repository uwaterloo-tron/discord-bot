import os
import discord
import logging
from discord.ext import commands
import config

print(f"STAGE={config.STAGE}")
print(f"LOG_LEVEL={config.LOG_LEVEL}")

if config.LOG_LEVEL not in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
    logging.error(f"Invalid log level: '{config.LOG_LEVEL}'. Falling back to WARNING")
    config.LOG_LEVEL = "WARNING"

logging.basicConfig(level=config.LOG_LEVEL)

status_msg = "development" if config.STAGE == "dev" else "with the fabric of reality"


async def _determine_prefix(bot, message):
    guild = message.guild
    # Only allow custom prefixs in guild
    if guild:
        guilds_col = config.db["guilds"]
        current_guild = guilds_col.find_one({"guild_id": guild.id})
        if current_guild is None or "prefix" not in current_guild.keys():
            return "?="
        return current_guild["prefix"]
    else:
        return "?="


intents = discord.Intents.all()
bot = commands.Bot(command_prefix=_determine_prefix, intents=intents, help_command=None)

initial_extensions = [f"cogs.{i[:-3]}" for i in os.listdir("cogs") if i.endswith(".py")]

# load cogs
for extension in initial_extensions:
    try:
        bot.load_extension(extension)
    except (commands.ExtensionNotFound, commands.ExtensionFailed) as e:
        logging.error(f"Failed to load extension {extension}")
        logging.error(e)


@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Game(name=status_msg), status=discord.Status.online
    )
    print("🔥 Yimin Wu is Online 🔥")


@bot.event
async def on_command_error(ctx, error):
    logging.error(error)


@bot.command()
@config.is_admin()
@commands.guild_only()
async def setprefix(ctx, prefix=""):
    # If empty arg, set to default prefix
    new_prefix = prefix or "?="
    guilds_col = config.db["guilds"]
    guilds_col.update_one({"guild_id": ctx.guild.id}, {"$set": {"prefix": new_prefix}})

    logging.debug(f"Changed prefix for guild '{ctx.guild.id}' to: {new_prefix}")
    await ctx.send("Prefix set!")


bot.run(config.TOKEN)
