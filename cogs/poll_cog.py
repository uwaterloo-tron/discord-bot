import discord
from discord.ext import tasks, commands
from discord_slash import SlashContext, cog_ext
import config
import json


class PollCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(name="poll", description="Start a poll (max 8 choices)")
    async def hello(
        self,
        ctx: SlashContext,
        message,
        anonymous,
        option1,
        option2,
        option3=None,
        option4=None,
        option5=None,
        option6=None,
        option7=None,
        option8=None,
    ):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("This is an admin-only command")
            return
        option_count = 0
        options = [
            option1,
            option2,
            option3,
            option4,
            option5,
            option6,
            option7,
            option8,
        ]
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
        options_string = ""
        emote_string = ""
        for idx, option in enumerate(options):
            if option is None:
                break
            else:
                options_string += "\n" + emojis[idx] + " \u200B " + option
                emote_string += emojis[idx] + " \u200B 0 \u200B "
                option_count += 1
        embed = discord.Embed(
            title=message,
            colour=0xFF69B4,
        )
        embed.add_field(name="Deadline: ", value="None", inline=False)
        embed.add_field(name="\u200B\nSelections: ", value=options_string, inline=False)
        embed.add_field(
            name="\u200B\nResults: ",
            value=emote_string,
            inline=False,
        )

        message = await ctx.send(embed=embed)
        for emote in emojis[:option_count]:
            await message.add_reaction(emote)
        polls_col = config.db["polls"]
        poll = {
            "guild_id": ctx.guild.id,
            "message_id": message.id,
            "selections": [[]] * option_count,
            "embed": json.dumps(embed.to_dict()),
        }
        await polls_col.insert_one(poll)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
        if payload.emoji.name not in emojis:
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
        index = emojis.index(payload.emoji.name)

        user_vote = await polls_col.find_one(
            {
                "message_id": payload.message_id,
                "guild_id": payload.guild_id,
                "selections": {"$elemMatch": {"$elemMatch": {"$eq": payload.user_id}}},
            }
        )
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
        embed = discord.Embed.from_dict(json.loads(poll["embed"]))
        embed.remove_field(-1)
        poll = await polls_col.find_one(
            {"message_id": payload.message_id, "guild_id": payload.guild_id}
        )
        values = " \u200B ".join(
            [f"{i} \u200B {len(j)}" for i, j in zip(emojis, poll["selections"])]
        )

        embed.add_field(
            name="\u200B\nResults: ",
            value=values,
            inline=False,
        )
        await message.edit(embed=embed)


def setup(bot):
    # Adds cog to bot from main.py
    bot.add_cog(PollCog(bot))
