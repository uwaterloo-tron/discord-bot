import logging
import discord
import config
from discord.ext import tasks, commands
from discord_slash import SlashContext, cog_ext
from discord_slash.utils.manage_commands import create_option, create_choice
import re
import emoji
import discord.utils as discutil


class RoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def reaction_handling(
        self, payload: discord.RawReactionActionEvent
    ) -> discord.role:

        # ignore all bot reactions
        if payload.user_id == self.bot.user.id:
            return None

        roles_col = config.db["role_reactions"]
        role_Add = await roles_col.find_one(
            {"message_id": payload.message_id, "guild_id": payload.guild_id}
        )
        # Ignore if message is not role reaction message or invalid reaction emoji
        if (
            role_Add is None
            or (
                payload.emoji.id is None
                and payload.emoji.name not in role_Add["emotes_written"]
            )
            or (
                payload.emoji.id is not None
                and payload.emoji.id not in role_Add["emote_ids"]
            )
        ):
            return None

        channel = self.bot.get_channel(payload.channel_id)

        # check if emote is a base emote or not then get the index we are looking for in the role list
        if payload.emoji.id is None:
            idx = role_Add["emotes_written"].index(payload.emoji.name)
        else:
            idx = role_Add["emote_ids"].index(payload.emoji.id)

        # get the role to add or delete
        return discutil.get(channel.guild.roles, id=role_Add["role_ids"][idx])

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        role = await self.reaction_handling(payload)
        if role:
            await payload.member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        role = await self.reaction_handling(payload)
        if role:
            channel = self.bot.get_channel(payload.channel_id)
            member = discutil.get(channel.guild.members, id=payload.user_id)
            await member.remove_roles(role)

    @cog_ext.cog_slash(
        name="RoleAdd",
        description="Add a Role/s (max 5 choices) ensure the bot has more permissions than the roles you try to add",
        options=[
            create_option(
                name="message",
                description="Whatever title u want for your reaction roles",
                option_type=3,
                required=True,
            ),
            create_option(
                name="role1",
                description="1st reaction role",
                option_type=8,
                required=True,
            ),
            create_option(
                name="emote1",
                description="Emote for Role 1",
                option_type=3,
                required=True,
            ),
            create_option(
                name="role2",
                option_type=8,
                description="2nd reaction role",
                required=False,
            ),
            create_option(
                name="emote2",
                description="Emote for Role 2",
                option_type=3,
                required=False,
            ),
            create_option(
                name="role3",
                option_type=8,
                description="3rd reaction role",
                required=False,
            ),
            create_option(
                name="emote3",
                description="Emote for Role 3",
                option_type=3,
                required=False,
            ),
            create_option(
                name="role4",
                option_type=8,
                description="4th reaction role",
                required=False,
            ),
            create_option(
                name="emote4",
                description="Emote for Role 4",
                option_type=3,
                required=False,
            ),
            create_option(
                name="role5",
                description="5th reaction role",
                option_type=8,
                required=False,
            ),
            create_option(
                name="emote5",
                description="Emote for Role 5",
                option_type=3,
                required=False,
            ),
        ],
    )
    async def createRoleAdd(
        self,
        ctx: SlashContext,
        message: str,
        role1: discord.role,
        emote1: str,
        role2: discord.role = None,
        emote2: str = None,
        role3: discord.role = None,
        emote3: str = None,
        role4: discord.role = None,
        emote4: str = None,
        role5: discord.role = None,
        emote5: str = None,
    ) -> None:

        roles_col = config.db["role_reactions"]
        option_count = 0
        roles = [role1, role2, role3, role4, role5]
        emotes = [emote1, emote2, emote3, emote4, emote5]
        role_string = ""
        available_emotes = [em_id.id for em_id in ctx.guild.emojis]
        emote_ids = []
        user = discutil.get(ctx.channel.guild.members, id=ctx.author_id)
        top_bot_role = ctx.guild.get_member(self.bot.user.id).top_role

        if not ctx.author.guild_permissions.administrator:
            await user.send("This is an admin-only command")
            return None

        roles_no_none = list(filter(None, roles))
        emotes_no_none = list(filter(None, emotes))

        if len(roles_no_none) != len(set(roles_no_none)) or len(emotes_no_none) != len(
            set(emotes_no_none)
        ):
            await user.send(
                "Your recent attempt to add a role reaction failed as you have attempted to create it"
                " with duplicate roles and/or emotes, which is not allowed"
            )
            return None

        # loop through all the inputted roles
        for idx, role in enumerate(roles):
            if role is None and emotes[idx] is None:
                break
            # checking if they inputted a role without an emote or vice versa
            elif role is None or emotes[idx] is None:
                await user.send(
                    "Your recent attempt to add a role reaction failed as you"
                    " do not have the same number of emotes as roles"
                )
                return None
            elif top_bot_role.position < role.position:
                await user.send(
                    "Your recent attempt to add a role reaction failed as you"
                    " have attempted to create a role reaction entitled: "
                    + role.name
                    + " which has more permissions than the bot, therefore the bot cannot grant users this role."
                )
                return None
            else:
                emote_id = re.match(r"<:\w+:(.*?)>", emotes[idx])
                EMOTE_LEN = 18
                if emoji.emoji_count(emotes[idx]) == 1:
                    emote_ids.append(None)  # used to show its unicode emote
                elif (
                    emote_id
                    and emote_id.group(1).isdigit()
                    and int(emote_id.group(1)) in available_emotes
                ):
                    emote_ids.append(int(emote_id.group(1)))

                else:
                    await user.send(
                        "Your recent attempt to add a role reaction failed as you have not properly selected an emote,"
                        " please select a default emote or one that is available to all members of the server where you"
                        " want to create the role reaction"
                    )
                    # print msg
                    return None

                # build out statement for the embed
                role_string += (
                    "\nFor: "
                    + role.mention
                    + " \u200B react with:  \u200B"
                    + emotes[idx]
                )
        embed = discord.Embed(
            title=message,
            colour=0xFF69B4,
        )
        embed.add_field(name="Roles", value=role_string, inline=False)
        message = await ctx.send(embed=embed)

        # add the reactions
        for emote in emotes[: len(emote_ids)]:
            await message.add_reaction(emote)
        roleAdd = {
            "guild_id": ctx.guild.id,
            "channel_id": ctx.channel.id,
            "message_id": message.id,
            "base_emote": [
                emote_id is None for emote_id in emote_ids
            ],  # useful for the future if editing added
            "role_ids": [role_id.id for role_id in roles[: len(emote_ids)]],
            "emote_ids": emote_ids,
            "emotes_written": emotes[: len(emote_ids)],
        }
        logging.debug(f"Adding RoleAdd to database. Message ID: {message.id}")
        await roles_col.insert_one(roleAdd)

    @commands.Cog.listener()
    async def on_raw_message_delete(
        self, payload: discord.RawMessageDeleteEvent
    ) -> None:

        roles_col = config.db["role_reactions"]

        # checks the database for the deleted message, if it contains it, it'll remove it
        await roles_col.delete_one(
            {"message_id": payload.message_id, "guild_id": payload.guild_id}
        )


def setup(bot):
    # Adds cog to bot from main.py
    bot.add_cog(RoleCog(bot))
