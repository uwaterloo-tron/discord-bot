from discord.ext import tasks, commands
import config


class PollCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    # adds cog to bot from main.py
    bot.add_cog(PollCog(bot))
