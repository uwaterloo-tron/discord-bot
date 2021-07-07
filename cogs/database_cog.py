from discord.ext import commands
import logging
import config


class DatabaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        logging.info(f"Joining guild: {guild.name}")
        guilds_col = config.db["guilds"]
        users_col = config.db["users"]

        guild_info = {
            "guild_id": guild.id,
            "prefix": "?=",
        }
        guilds_col.insert_one(guild_info)

        users_list = []
        for member in guild.members:
            users_list.append(
                {
                    "user_id": member.id,
                    "guild_id": guild.id,
                    "bot": member.bot,
                }
            )

        guild_users = users_col.insert_many(users_list)
        logging.info(f"Inserted {len(guild_users.inserted_ids)} new users")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        logging.info(f"Leaving guild: {guild.name}")
        guilds_col = config.db["guilds"]
        users_col = config.db["users"]

        guilds_col.delete_one({"guild_id": guild.id})
        guild_users = users_col.delete_many({"guild_id": guild.id})

        logging.info(f"Deleted {guild_users.deleted_count} users")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        users_col = config.db["users"]
        user_dict = {
            "user_id": member.id,
            "guild_id": member.guild.id,
            "bot": member.bot,
        }
        users_col.insert_one(user_dict)

    @commands.Cog.listener()
    async def on_member_leave(self, member):
        users_col = config.db["users"]
        user_dict = {
            "user_id": member.id,
            "guild_id": member.guild.id,
            "bot": member.bot,
        }
        users_col.delete_one(user_dict)


def setup(bot):
    # adds cog to bot from main.py
    bot.add_cog(DatabaseCog(bot))
