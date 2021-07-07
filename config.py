import os
import pymongo
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
STAGE = os.getenv("STAGE", "dev")
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING")

mongo_client = pymongo.MongoClient("mongodb")
db = mongo_client["discord"]


# Common command checks


def is_admin():
    async def predicate(ctx):
        if ctx.message.author.guild_permissions.administrator:
            return True
        await ctx.send("This is an admin-only command")
        return False

    return commands.check(predicate)
