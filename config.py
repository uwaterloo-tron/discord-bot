import os
import discord
import motor.motor_asyncio
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
STAGE = os.getenv("STAGE", "dev")
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING")

mongo_client = motor.motor_asyncio.AsyncIOMotorClient("mongodb")
db = mongo_client["discord"]


# Common command checks


async def get_prefix(guild: discord.Guild):
    # Only allow prefixs in guild
    if guild:
        guilds_col = db["guilds"]
        current_guild = await guilds_col.find_one({"guild_id": guild.id})
        if current_guild is None or "prefix" not in current_guild.keys():
            # default prefix
            return "?="
        return current_guild["prefix"]
    return ""


def is_admin():
    async def predicate(ctx):
        if ctx.message.author.guild_permissions.administrator:
            return True
        await ctx.send("This is an admin-only command <a:NOP:799726788132732928>")
        return False

    return commands.check(predicate)
