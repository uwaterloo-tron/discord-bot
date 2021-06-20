import discord
from discord.ext import commands
import config

print(f"STAGE={config.STAGE}")
status_msg = "development" if config.STAGE == "dev" else "with your mom LOL"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='?wu', intents=intents, help_command=None)


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name=status_msg), status=discord.Status.online)
    print("🔥 Yimin Wu is Online 🔥")


@bot.event
async def on_command_error(ctx, error):
    print(error)
    await ctx.send('`invalid command`')


bot.run(config.TOKEN)
