import logging
import pytz
import discord
from discord.ext import tasks, commands
from discord_slash import SlashContext, cog_ext
from discord_slash.utils.manage_commands import create_option, create_choice
from dateutil.parser import ParserError
import dateparser
import datetime
import config
import json


class PollCog(commands.Cog):
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

    def __init__(self, bot):
        self.bot = bot
        self.deadline_check.start()

    @tasks.loop(seconds=30)
    async def deadline_check(self):
        polls_col = config.db["polls"]
        polls_with_deadlines = polls_col.find({"deadline": {"$ne": None}})

        present_datetime = datetime.datetime.now(pytz.utc)

        async for poll in polls_with_deadlines:
            if pytz.timezone("UTC").localize(poll["deadline"]) <= present_datetime:
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
    ):
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

        poll = {
            "guild_id": ctx.guild.id,
            "channel_id": ctx.channel.id,
            "message_id": message.id,
            "selections": [[]] * option_count,
            "embed": json.dumps(embed.to_dict()),
            "deadline": None,
            "anonymous": anonymous,
        }
        await polls_col.insert_one(poll)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if payload.emoji.name not in self.emojis:
            return
        polls_col = config.db["polls"]
        poll = await polls_col.find_one(
            {"message_id": payload.message_id, "guild_id": payload.guild_id}
        )
        if poll is None:
            return
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

        await polls_col.update_one(
            {"message_id": payload.message_id, "guild_id": payload.guild_id},
            {"$push": {f"selections.{index}": payload.user_id}},
        )

        if not poll["anonymous"]:
            embed = discord.Embed.from_dict(json.loads(poll["embed"]))
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
    async def on_raw_message_delete(self, payload):
        message = payload.cached_message
        polls_col = config.db["polls"]
        poll = await polls_col.find_one(
            {"message_id": message.id, "guild_id": message.guild.id}
        )
        if poll is None:
            return
        await message.channel.send(
            "Please Close the poll before attempting to delete it :pray:"
        )
        embed = discord.Embed.from_dict(json.loads(poll["embed"]))
        embed.remove_field(-1)
        values = " \u200B ".join(
            [f"{i} \u200B {len(j)}" for i, j in zip(self.emojis, poll["selections"])]
        )
        embed.add_field(
            name="\u200B\nResults: ",
            value=values,
            inline=False,
        )
        if poll["deadline"] is not None:
            embed.remove_field(0)
            embed.insert_field_at(
                index=0,
                name="Deadline: ",
                value=pytz.timezone("America/Toronto")
                .localize(poll["deadline"])
                .strftime("%Y/%m/%d %I:%M %p %Z"),
                inline=False,
            )

        new_message = await message.channel.send(embed=embed)

        for emote in self.emojis[: len(poll["selections"])]:
            await new_message.add_reaction(emote)

        await polls_col.update_one(
            {"message_id": message.id, "guild_id": message.guild.id},
            {"$set": {"message_id": new_message.id}},
        )

    @commands.group()
    @config.is_admin()
    async def poll(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Invalid: Use one of the following subcommands: deadline, close, list"
            )

    @poll.command()
    async def close(self, ctx):
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
            await ctx.send("This ain't a poll :clown:")
            return

        await ctx.message.delete()
        await self.do_close(reply, "MANUALLY CLOSED")

    @poll.command()
    async def list(self, ctx):
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
    async def deadline(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Use one of the following subcommands: set, remove")

    @deadline.command()
    async def set(self, ctx, *, date_string):
        if ctx.message.reference is None:
            await ctx.send(
                "Invalid: You must reply to the poll you want to add a deadline for"
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
            await ctx.send("This ain't a poll :clown:")
            return

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
                'Invalid: Please enter in a duration for example: "In 5 days and 5 hours and 30 minutes" :frowning'
            )
            return
        if (selected_date - datetime.datetime.now(pytz.utc)).total_seconds() < 59:
            await ctx.send(
                "Invalid: You cannot enter a deadline less than 1 minute long :frowning:"
            )
            return
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
        embed = discord.Embed.from_dict(json.loads(poll["embed"]))
        embed.remove_field(0)
        embed.insert_field_at(
            index=0,
            name="Deadline: ",
            value=selected_date.strftime("%Y/%m/%d %I:%M %p %Z"),
            inline=False,
        )
        poll_message = await ctx.channel.fetch_message(reply)
        await poll_message.edit(embed=embed)

    @deadline.command()
    async def remove(self, ctx):
        if ctx.message.reference is None:
            await ctx.send(
                "Invalid: You must reply to the poll you want to add a deadline for"
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
            await ctx.send("This ain't a poll :clown:")
            return

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
        embed = discord.Embed.from_dict(json.loads(poll["embed"]))
        embed.remove_field(0)
        embed.insert_field_at(
            index=0,
            name="Deadline: ",
            value="None",
            inline=False,
        )
        poll_message = await ctx.channel.fetch_message(reply)
        await poll_message.edit(embed=embed)

    async def do_close(self, message_id: int, reason: str):
        """
        Close a poll with the given message id
        :param message_id: is the message id of the poll which is wanted to be closed *must be in the database*
        :param reason: the footer explaining why the poll was closed
        :return: None
        """
        polls_col = config.db["polls"]
        poll = await polls_col.find_one({"message_id": message_id})
        channel = self.bot.get_channel(poll["channel_id"])
        poll_message = await channel.fetch_message(message_id)

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
