import os
import discord
import logging
from discord.ext import commands
import config
from discord_slash import SlashCommand

print(f"STAGE={config.STAGE}")
print(f"LOG_LEVEL={config.LOG_LEVEL}")

if config.LOG_LEVEL not in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
    logging.error(f"Invalid log level: '{config.LOG_LEVEL}'. Falling back to WARNING")
    config.LOG_LEVEL = "WARNING"

logging.basicConfig(level=config.LOG_LEVEL)

status_msg = "development" if config.STAGE == "dev" else "with the fabric of reality"


async def _determine_prefix(bot: commands.Bot, message: discord.Message):
    guild = message.guild
    return await config.get_prefix(guild)


intents = discord.Intents.all()
bot = commands.Bot(command_prefix=_determine_prefix, intents=intents)
slash = SlashCommand(bot, sync_commands=True)
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
    print("🔥 Tron Bot is Online 🔥")


@bot.event
async def on_message(message: discord.Message):
    guild = message.guild
    if guild:
        if message.content == f"<@!{bot.user.id}>":
            prefix = await config.get_prefix(guild)
            embed = discord.Embed(
                title="",
                description=f"**This guild's command prefix is:** `{prefix}`",
                color=discord.Color.red(),
            )
            await message.channel.send(embed=embed)
        else:
            await bot.process_commands(message)


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if config.STAGE != "prod":
        await ctx.send(f"`Error: {error}`")
    logging.error(error)


@bot.command()
@config.is_admin()
@commands.guild_only()
async def setprefix(ctx, prefix: str = "", who: discord.User = None):
    """
    Sets the bot's command prefix for the current guild.

    :param prefix: The new prefix for the guild. Resets to default if None given. [Optional]
    :param who: Specify which bot you are addressing in case there are overlapping prefixes. [Optional]
    """
    print(who)
    if who is not None and who != bot.user:
        return

    # If empty arg, set to default prefix
    new_prefix = prefix or "?="
    guilds_col = config.db["guilds"]
    guilds_col.update_one({"guild_id": ctx.guild.id}, {"$set": {"prefix": new_prefix}})

    logging.debug(f"Changed prefix for guild '{ctx.guild.id}' to: {new_prefix}")
    await ctx.send("Prefix set!")


bot.run(config.TOKEN)
