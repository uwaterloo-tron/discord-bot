import logging
import pytz
import discord
import dateparser
import datetime
import config
from discord.ext import tasks, commands
from discord_slash import SlashContext, cog_ext
from discord_slash.utils.manage_commands import create_option, create_choice
from dateutil.parser import ParserError
from typing import Union


class PollCog(commands.Cog):
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

    def __init__(self, bot):
        self.bot = bot
        self.deadline_check.start()

    @tasks.loop(seconds=30)
    async def deadline_check(self):
        """
        Find polls whose deadline has passed and closes them.
        """
        polls_col = config.db["polls"]
        polls_with_deadlines = polls_col.find({"deadline": {"$ne": None}})

        present_datetime = datetime.datetime.now(pytz.utc)

        async for poll in polls_with_deadlines:
            if pytz.timezone("UTC").localize(poll["deadline"]) <= present_datetime:
                logging.debug(
                    f"Deadline passed for poll. Message ID: {poll['message_id']}"
                )
                await self.do_close(poll["message_id"], "DEADLINE PASSED")

    @deadline_check.before_loop
    async def before_deadline_check(self):
        await self.bot.wait_until_ready()

    @cog_ext.cog_slash(
        name="poll",
        description="Start a poll (max 8 choices)",
        options=[
            create_option(
                name="message",
                description="The question your poll is asking",
                option_type=3,
                required=True,
            ),
            create_option(
                name="anonymous",
                description="Allow users to see results before the poll is closed",
                option_type=3,
                required=True,
                choices=[
                    create_choice(name="No", value="False"),
                    create_choice(name="Yes", value="True"),
                ],
            ),
            create_option(
                name="choice1",
                description="Choice 1",
                option_type=3,
                required=True,
            ),
            create_option(
                name="choice2",
                description="Choice 2",
                option_type=3,
                required=True,
            ),
            create_option(
                name="choice3",
                description="Choice 3",
                option_type=3,
                required=False,
            ),
            create_option(
                name="choice4",
                description="Choice 4",
                option_type=3,
                required=False,
            ),
            create_option(
                name="choice5",
                description="Choice 5",
                option_type=3,
                required=False,
            ),
            create_option(
                name="choice6",
                description="Choice 6",
                option_type=3,
                required=False,
            ),
            create_option(
                name="choice7",
                description="Choice 7",
                option_type=3,
                required=False,
            ),
            create_option(
                name="choice8",
                description="Choice 8",
                option_type=3,
                required=False,
            ),
        ],
    )
    async def create_poll(
        self,
        ctx: SlashContext,
        message: str,
        anonymous: str,
        choice1: str,
        choice2: str,
        choice3: str = None,
        choice4: str = None,
        choice5: str = None,
        choice6: str = None,
        choice7: str = None,
        choice8: str = None,
    ) -> None:
        """
        Slash command to create a new poll for the guild.

        :param message: The question your poll is asking.
        :param anonymous: If users should see results before the poll is closed.
        :param choice1: Choice 1.
        :param choice2: Choice 2.
        :param choice3: Choice 3. [Optional]
        :param choice4: Choice 4. [Optional]
        :param choice5: Choice 5. [Optional]
        :param choice6: Choice 6. [Optional]
        :param choice7: Choice 7. [Optional]
        :param choice8: Choice 8. [Optional]
        """
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("This is an admin-only command")
            return
        polls_col = config.db["polls"]
        if await polls_col.count_documents({"guild_id": ctx.guild.id}) == 5:
            await ctx.send("You already have 5 active polls as follows:")
            await self.list(ctx)
            return

        option_count = 0
        options = [
            choice1,
            choice2,
            choice3,
            choice4,
            choice5,
            choice6,
            choice7,
            choice8,
        ]

        # Create embed for poll
        options_string = ""
        emote_string = ""
        for idx, option in enumerate(options):
            if option is None:
                break
            else:
                options_string += "\n" + self.emojis[idx] + " \u200B " + option
                emote_string += self.emojis[idx] + " \u200B 0 \u200B "
                option_count += 1
        embed = discord.Embed(
            title=message,
            colour=0xFF69B4,
        )
        embed.add_field(name="Deadline: ", value="None", inline=False)
        embed.add_field(name="\u200B\nSelections: ", value=options_string, inline=False)

        anonymous = anonymous == "True"

        # Don't include the "results" field if the poll is anonymous
        if not anonymous:
            embed.add_field(
                name="\u200B\nResults: ",
                value=emote_string,
                inline=False,
            )

        message = await ctx.send(embed=embed)
        for emote in self.emojis[:option_count]:
            await message.add_reaction(emote)

        # Add new poll to database
        poll = {
            "guild_id": ctx.guild.id,
            "channel_id": ctx.channel.id,
            "message_id": message.id,
            "selections": [[]] * option_count,
            "deadline": None,
            "anonymous": anonymous,
        }
        logging.debug(f"Adding poll to database. Message ID: {message.id}")
        await polls_col.insert_one(poll)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Handle votes.
        """
        # Ignore if reaction is from bot
        if payload.user_id == self.bot.user.id:
            return

        # Ignore if invalid reaction emoji
        if payload.emoji.name not in self.emojis:
            return

        polls_col = config.db["polls"]
        poll = await polls_col.find_one(
            {"message_id": payload.message_id, "guild_id": payload.guild_id}
        )
        if poll is None:
            return

        logging.debug(
            f"Handling vote for poll. Vote: {payload.emoji.name}, Message ID: {payload.message_id}"
        )
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        await message.remove_reaction(payload.emoji.name, payload.member)
        index = self.emojis.index(payload.emoji.name)

        # Find if user has already voted before
        user_vote = await polls_col.find_one(
            {
                "message_id": payload.message_id,
                "guild_id": payload.guild_id,
                "selections": {"$elemMatch": {"$elemMatch": {"$eq": payload.user_id}}},
            }
        )
        # Remove previous vote if user voted before (1 vote per user)
        if user_vote is not None:
            for idx, _ in enumerate(poll["selections"]):
                await polls_col.update_one(
                    {"message_id": payload.message_id, "guild_id": payload.guild_id},
                    {"$pull": {f"selections.{idx}": payload.user_id}},
                )

        # Set user's vote in database
        await polls_col.update_one(
            {"message_id": payload.message_id, "guild_id": payload.guild_id},
            {"$push": {f"selections.{index}": payload.user_id}},
        )

        # Update "results" field in embed if the poll is not anonymous
        if not poll["anonymous"]:
            embed = message.embeds[0]
            embed.remove_field(-1)
            poll = await polls_col.find_one(
                {"message_id": payload.message_id, "guild_id": payload.guild_id}
            )
            values = " \u200B ".join(
                [
                    f"{i} \u200B {len(j)}"
                    for i, j in zip(self.emojis, poll["selections"])
                ]
            )

            embed.add_field(
                name="\u200B\nResults: ",
                value=values,
                inline=False,
            )
            await message.edit(embed=embed)

    @commands.Cog.listener()
    async def on_raw_message_delete(
        self, payload: discord.RawMessageDeleteEvent
    ) -> None:
        """
        Handle if poll message is deleted.
        """
        polls_col = config.db["polls"]
        await polls_col.delete_one(
            {"message_id": payload.message_id, "guild_id": payload.guild_id}
        )

    @commands.group(
        help='Commands for polls created with "/poll".\nAll commands MUST be done in a reply to a poll.'
    )
    @config.is_admin()
    async def poll(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Invalid: Use one of the following subcommands: `deadline`, `close`, `list`\n"
                f"Type `{await config.get_prefix(ctx.guild)}help poll` for more details."
            )

    @poll.command()
    async def close(self, ctx: commands.Context) -> None:
        """
        Close the selected poll. Reply to the poll you want to select.
        """

        # Make sure the command is replying to a valid poll message
        if ctx.message.reference is None:
            await ctx.send("Invalid: you must reply to the poll you want to close")
            return

        reply = ctx.message.reference.message_id

        polls_col = config.db["polls"]
        poll = await polls_col.find_one(
            {
                "guild_id": ctx.guild.id,
                "channel_id": ctx.channel.id,
                "message_id": reply,
            }
        )
        if poll is None:
            await ctx.send("This ain't an active poll :clown:")
            return

        logging.debug(f"Manually closing poll. Message ID: {reply}")
        await ctx.message.delete()  # Delete the user's command message to reduce clutter
        await self.do_close(reply, "MANUALLY CLOSED")

    @poll.command()
    async def list(
        self, ctx: Union[commands.Context, SlashContext]
    ) -> None:  # Note: python 3.10 now allows: "commands.Context | SlashContext" notation instead of Union
        """
        List all currently active polls in an embed.
        """
        logging.debug(f"Listing all active polls. Guild ID: {ctx.guild.id}")
        polls_col = config.db["polls"]
        guild_polls = polls_col.find({"guild_id": ctx.guild.id})

        poll_links_embed = discord.Embed(title="Active Polls")

        count = 0

        async for poll in guild_polls:
            count += 1
            poll_links_embed.add_field(
                name=f"Poll #{count}",
                value=f"https://discord.com/channels/{poll['guild_id']}/{poll['channel_id']}/{poll['message_id']}",
                inline=False,
            )

        if count == 0:
            poll_links_embed = discord.Embed(title="Active Polls", description="None")

        await ctx.send(embed=poll_links_embed)

    @poll.group()
    async def deadline(self, ctx: commands.Context) -> None:
        """
        Set or remove the deadline for a poll.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Use one of the following subcommands: `set`, `remove`\n"
                f"Type `{await config.get_prefix(ctx.guild)}help poll deadline` for more details."
            )

    @deadline.command()
    async def set(self, ctx: commands.Context, *, date_string: str) -> None:
        """
        Set a deadline for a poll. Reply to the poll you want to select.

        :param date_string: The date of the deadline, must be parsable (https://github.com/scrapinghub/dateparser).
        """
        if ctx.message.reference is None:
            await ctx.send(
                "Invalid: You must reply to the poll you want to add a deadline for"
            )
            return

        # Get the selected poll
        reply = ctx.message.reference.message_id
        polls_col = config.db["polls"]
        poll = await polls_col.find_one(
            {
                "guild_id": ctx.guild.id,
                "channel_id": ctx.channel.id,
                "message_id": reply,
            }
        )
        if poll is None:
            await ctx.send("This ain't an active poll :clown:")
            return

        logging.debug(f"Setting a new deadline for a poll. Message ID {reply}")

        # Parse the given deadline date
        try:
            selected_date = dateparser.parse(
                date_string,
                settings={
                    "TIMEZONE": "America/Toronto",
                    "RETURN_AS_TIMEZONE_AWARE": True,
                },
            )
            if selected_date is None:
                raise ParserError
        except (ParserError, OverflowError):
            await ctx.send(
                'Invalid: You must enter a valid date. Example: "In 5 days and 5 hours and 30 minutes" :frowning:'
            )
            return

        # Only allow deadlines >1 minute from current time
        # to prevent weird activity with the deadline_check
        if (selected_date - datetime.datetime.now(pytz.utc)).total_seconds() < 59:
            await ctx.send(
                "Invalid: You cannot enter a deadline less than 1 minute long :frowning:"
            )
            return

        # Set new deadline in database
        polls_col = config.db["polls"]
        await polls_col.update_one(
            {
                "guild_id": ctx.guild.id,
                "channel_id": ctx.channel.id,
                "message_id": reply,
            },
            {"$set": {"deadline": selected_date}},
        )
        poll = await polls_col.find_one(
            {
                "guild_id": ctx.guild.id,
                "channel_id": ctx.channel.id,
                "message_id": reply,
            }
        )

        # Set new deadline in poll message embed
        poll_message = await ctx.channel.fetch_message(reply)
        embed = poll_message.embeds[0]
        embed.remove_field(0)
        embed.insert_field_at(
            index=0,
            name="Deadline: ",
            value=selected_date.strftime("%Y/%m/%d %I:%M %p %Z"),
            inline=False,
        )
        await poll_message.edit(embed=embed)

    @deadline.command()
    async def remove(self, ctx: commands.Context) -> None:
        """
        Remove the deadline for a poll. Reply to the poll you want to select.
        """
        if ctx.message.reference is None:
            await ctx.send(
                "Invalid: You must reply to the poll you want to remove a deadline from"
            )
            return

        reply = ctx.message.reference.message_id
        polls_col = config.db["polls"]
        poll = await polls_col.find_one(
            {
                "guild_id": ctx.guild.id,
                "channel_id": ctx.channel.id,
                "message_id": reply,
            }
        )
        if poll is None:
            await ctx.send("This ain't an active poll :clown:")
            return

        if poll["deadline"] is None:
            await ctx.send("This poll already has no deadline")
            return

        logging.debug(f"Removing deadline for poll. Message ID: {reply}")

        await polls_col.update_one(
            {
                "guild_id": ctx.guild.id,
                "channel_id": ctx.channel.id,
                "message_id": reply,
            },
            {"$set": {"deadline": None}},
        )
        poll = await polls_col.find_one(
            {
                "guild_id": ctx.guild.id,
                "channel_id": ctx.channel.id,
                "message_id": reply,
            }
        )
        poll_message = await ctx.channel.fetch_message(reply)
        embed = poll_message.embeds[0]
        embed.remove_field(0)
        embed.insert_field_at(
            index=0,
            name="Deadline: ",
            value="None",
            inline=False,
        )
        await poll_message.edit(embed=embed)

    async def do_close(self, message_id: int, reason: str) -> None:
        """
        Close the poll with the given message id.

        :param message_id: The message id of the poll to be closed *must be in the database*.
        :param reason: The footer explaining why the poll was closed.
        """
        polls_col = config.db["polls"]
        poll = await polls_col.find_one({"message_id": message_id})
        channel = self.bot.get_channel(poll["channel_id"])
        poll_message = await channel.fetch_message(message_id)

        # Edit poll embed to show it is closed
        embed = poll_message.embeds[0]
        embed.set_footer(text=f"****{reason}****")
        embed.set_thumbnail(
            url="https://raw.githubusercontent.com/uwaterloo-tron/discord-bot/master/assets/images/poll_closed.png"
        )

        # Add back in the "results" field if the poll was anonymous
        if poll["anonymous"]:
            values = " \u200B ".join(
                [
                    f"{i} \u200B {len(j)}"
                    for i, j in zip(self.emojis, poll["selections"])
                ]
            )

            embed.add_field(
                name="\u200B\nResults: ",
                value=values,
                inline=False,
            )

        await poll_message.edit(embed=embed)
        await poll_message.reply(f'The following poll has ended: "{embed.title}"')

        logging.debug(f"Removing poll from database. Message ID: {message_id}")
        await polls_col.delete_one({"message_id": message_id})


def setup(bot):
    # Adds cog to bot from main.py
    bot.add_cog(PollCog(bot))
