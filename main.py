import os
import discord
import logging
from discord.ext import commands
import config

print(f"STAGE={config.STAGE}")
print(f"LOG_LEVEL={config.LOG_LEVEL}")

if config.LOG_LEVEL not in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
    logging.error(f"Invalid log level: '{config.LOG_LEVEL}'. Falling back to WARNING")
    config.LOG_LEVEL = 'WARNING'

logging.basicConfig(level=config.LOG_LEVEL)

status_msg = "development" if config.STAGE == "dev" else "with the fabric of reality"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='?=', intents=intents, help_command=None)

initial_extensions = [f"cogs.{i[:-3]}" for i in os.listdir('cogs') if i.endswith('.py')]

# load cogs
if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except (commands.ExtensionNotFound, commands.ExtensionFailed) as e:
            print(f'Failed to load extension {extension}')
            print(e)


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name=status_msg), status=discord.Status.online)
    print("🔥 Yimin Wu is Online 🔥")


@bot.event
async def on_command_error(ctx, error):
    print(error)
    await ctx.send('`invalid command`')


bot.run(config.TOKEN)
