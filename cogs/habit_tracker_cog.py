import logging
import os
import pytz
import discord
import datetime
import aiohttp
from tabulate import tabulate
from typing import Tuple
import config
import io
from discord.ext import tasks, commands
from discord_slash import SlashContext, cog_ext
from discord_slash.utils.manage_commands import create_option
from datetime import datetime, timedelta
from discord import Guild
import imgkit

_FREQUENCY_OPTIONS = ["weekly", "monthly"]
_DEV_FREQUENCY_OPTIONS = ["10seconds"]


class HabitTrackerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_habits.start()
        self.max_habits_per_guild = 2
        if config.STAGE != "prod":
            self.bot.add_command(
                commands.Command(self.update_habits, name="update_habits")
            )

    def get_period_bounds(self, frequency: str) -> Tuple[datetime, datetime]:
        """
        Gets the bounds for the current period depending on the frequency selected
        """
        now = datetime.now(pytz.utc)

        if frequency == "weekly":
            # weekday(): Monday=0 ... Sunday=6
            # We want to shift so Sunday=0 ... Saturday=6
            # Calculate days since last Sunday
            days_since_sunday = (now.weekday() + 1) % 7
            start = (now - timedelta(days=days_since_sunday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = start + timedelta(days=7)
        elif config.STAGE != "prod" and frequency == "10seconds":
            # Calculate the start of the current 10-second interval
            # e.g. if seconds = 34, start = seconds 30, end = seconds 40
            seconds = now.second
            interval_start_seconds = (seconds // 10) * 10
            start = now.replace(second=interval_start_seconds, microsecond=0)
            end = start + timedelta(seconds=10)
        else:
            # Monthly period: from first day of month 00:00 to first day of next month 00:00
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = next_month.replace(hour=0, minute=0, second=0, microsecond=0)

        return start, end

    def update_totals(self, habit: dict) -> dict:
        """Update the total counts, types, and missed goals from current period logs."""
        current_users = habit["log_periods"]["current"].get("users", {})
        total_users = habit.get("total", {})

        for user_id, user_data in current_users.items():
            total = user_data.get("count", 0)
            met_goal = total >= habit["goal"]
            breakdown = user_data.get("types", {})

            # Initialize total entry if missing
            if user_id not in total_users:
                total_users[user_id] = {
                    "types": {k: 0 for k in habit["types"]},
                    "count": 0,
                    "missed_goals": 0,
                    "achieved_goals": 0,
                }

            # Accumulate counts
            total_users[user_id]["count"] += total
            for activity_type, count in breakdown.items():
                total_users[user_id]["types"][activity_type] = (
                    total_users[user_id]["types"].get(activity_type, 0) + count
                )

            # Track missed goals
            if not met_goal:
                total_users[user_id]["missed_goals"] += 1
            else:
                total_users[user_id]["achieved_goals"] += 1

        return total_users

    """
    Renders an image file for the weekly summary of a given habit.

    The file is saved as 'habit_summary.png' in the current directory.
    """

    def generate_weekly_summary_image(self, guild: Guild, habit: dict) -> None:

        activity_types = habit.get("types", [])
        headers = ["User", "Total", "Goal Met"] + activity_types
        rows = []

        current_users = habit.get("log_periods", {}).get("current", {}).get("users", {})
        goal = habit.get("goal", 0)

        # Parse the known-good ISO datetime strings
        start_dt = datetime.fromisoformat(habit["log_periods"]["current"]["start"])
        end_dt = datetime.fromisoformat(habit["log_periods"]["current"]["end"])
        period_str = f"Period: **{start_dt.strftime('%Y-%m-%d')}** to **{end_dt.strftime('%Y-%m-%d')}**"

        for user_id, user_data in current_users.items():
            total = user_data.get("count", 0)
            met_goal = "✔" if total >= goal else "✘"
            types = user_data.get("types", {})
            activity_counts = [types.get(act, 0) for act in activity_types]
            user = guild.get_member(int(user_id))
            user_name = user.name if user else f"User ID {user_id}"
            rows.append([user_name, total, met_goal] + activity_counts)

        # Create table as HTML, then render with CSS into an image
        table = tabulate(rows, headers=headers, tablefmt="html", stralign="center")
        imgkit.from_string(
            table, "habit_summary.png", css="assets/stylesheets/habit_table_dark.css"
        )

    """
    Renders an image file for the total summary of a given habit.

    The file is saved as 'totals_table.png' in the current directory.
    """

    def generate_total_summary_image(self, guild: Guild, habit: dict) -> None:
        headers = ["User"] + habit["types"] + ["Total", "Met Goals", "Missed Goals"]
        rows = []

        for user_id, data in habit.get("total", {}).items():
            user = guild.get_member(int(user_id))
            user_name = user.name if user else f"User ID {user_id}"

            types = data.get("types", {})
            row = [user_name]

            for act_type in habit["types"]:
                row.append(types.get(act_type, 0))

            row.append(data.get("count", 0))
            row.append(data.get("achieved_goals", 0))
            row.append(data.get("missed_goals", 0))
            rows.append(row)

        # Sort rows by "Missed Goals" in descending order (last column)
        rows.sort(key=lambda r: r[-1], reverse=True)

        # Create table as HTML, then render with CSS into an image
        table = tabulate(rows, headers=headers, tablefmt="html", stralign="center")
        imgkit.from_string(
            table, "totals_table.png", css="assets/stylesheets/habit_table_dark.css"
        )

    @tasks.loop(hours=24)
    async def check_habits(self) -> None:
        """
        Automatically checks and updates habits standings if necessary
        """
        await self.update_habits(None)

    @check_habits.before_loop
    async def before_check_habits(self):
        await self.bot.wait_until_ready()

    @cog_ext.cog_slash(
        name="add_habit",
        description="Create a habit (setup phase only)",
        options=[
            create_option(
                name="name",
                description="Name of the habit",
                option_type=3,
                required=True,
            ),
            create_option(
                name="frequency",
                description="How often you want to track your goals",
                option_type=3,
                required=True,
                choices=(
                    _DEV_FREQUENCY_OPTIONS + _FREQUENCY_OPTIONS
                    if config.STAGE != "prod"
                    else _FREQUENCY_OPTIONS
                ),
            ),
            create_option(
                name="goal", description="Goal per period", option_type=4, required=True
            ),
            create_option(
                name="types",
                description="Comma-separated list of allowed activity types",
                option_type=3,
                required=True,
            ),
        ],
    )
    async def create_tracked_habit(
        self, ctx: SlashContext, name: str, frequency: str, goal: int, types: str
    ) -> None:
        """
        Slash command to create a tracked habit for the guild.

        :param name: The name of the habit you want to track.
        :param frequency: The frequency you want to check this habit at
        :param goal: The amount of times you want to do this habit within one period.
        :param types: The allowed activity types that are being tracked
        """
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("This is an admin-only command")
            return
        tracked_habit_cols = config.db["habits"]
        if (
            await tracked_habit_cols.count_documents({"guild_id": ctx.guild.id})
            >= self.max_habits_per_guild
        ):
            await ctx.send("You cannot have more than two active habit trackers:")
            await self.list_habits(ctx)
            return
        existing = await tracked_habit_cols.find_one(
            {"guild_id": ctx.guild.id, "name": name}
        )
        if existing:
            await ctx.send(f"A habit tracker with the name '{name}' already exists.")
            return

        start, end = self.get_period_bounds(frequency)
        allowed_types = [t.strip().lower() for t in types.split(",")]
        habit = {
            "guild_id": ctx.guild.id,
            "channel_id": ctx.channel.id,
            "name": name,
            "frequency": frequency,
            "goal": goal,
            "types": allowed_types,
            "users": [],
            "log_periods": {
                "current": {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "users": {},  # {user_id: {"types": {...}, "count": int}}
                },
                "total": {},  # user_id: {"types": {...}, "count": int, "achieved_goals": int, "missed_goals": int}
            },
            "started": False,
        }
        logging.debug(f"Adding New Tracked Habit: {name}")
        await tracked_habit_cols.insert_one(habit)
        await ctx.send(
            f"Successfully added habit: {name}, to the tracker list. Add all the "
            f"required members with /add_user_to_habit, and log with /log"
        )

    @cog_ext.cog_slash(
        name="add_user_to_habit",
        description="Add a user to a habit",
        options=[
            create_option(
                name="habit_name",
                description="Habit name",
                option_type=3,
                required=True,
            ),
            create_option(
                name="user", description="User to add", option_type=6, required=True
            ),
        ],
    )
    async def add_user_to_habit(self, ctx, habit_name, user) -> None:
        habits_col = config.db["habits"]
        guild_id = ctx.guild.id
        user_id = user.id

        habit = await habits_col.find_one({"guild_id": guild_id, "name": habit_name})
        if not habit:
            await ctx.send("❌ Habit not found.")
            return
        if user_id in habit["users"]:
            await ctx.send("⚠️ User is already part of the habit.")
            return

        empty_types = {type: 0 for type in habit["types"]}

        update = {
            "$push": {"users": user_id},
            "$set": {
                f"log_periods.current.users.{user_id}": {
                    "types": empty_types,
                    "count": 0,
                },
                f"total.{user_id}": {
                    "types": empty_types,
                    "count": 0,
                    "achieved_goals": 0,
                    "missed_goals": 0,
                },
            },
        }
        await habits_col.update_one({"_id": habit["_id"]}, update)
        await ctx.send(f"Added {user.name} to '{habit_name}'")

    @cog_ext.cog_slash(
        name="start_habit",
        description="Start a habit after setup",
        options=[
            create_option(
                name="habit", description="Habit name", option_type=3, required=True
            ),
        ],
    )
    async def start_habit(self, ctx, habit) -> None:
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("This is an admin-only command")
            return
        habits_col = config.db["habits"]
        guild_id = ctx.guild.id

        habit_doc = await habits_col.find_one({"guild_id": guild_id, "name": habit})
        if not habit_doc:
            await ctx.send("❌ Habit not found.")
            return
        if habit_doc["started"]:
            await ctx.send("⚠️ Already started.")
            return
        if not habit_doc["users"]:
            await ctx.send("⚠️ You must add at least one user first.")
            return

        await habits_col.update_one(
            {"guild_id": guild_id, "name": habit}, {"$set": {"started": True}}
        )
        await ctx.send(f"🚀 Habit `{habit}` has started!")

    @cog_ext.cog_slash(
        name="log",
        description="Log an activity for a habit",
        options=[
            create_option(
                "habit_name",
                option_type=3,
                description="Name of the habit",
                required=True,
            ),
            create_option(
                "type", option_type=3, description="The habit subtype", required=True
            ),
            create_option(
                "user1",
                option_type=6,
                description="First Additional user",
                required=False,
            ),
            create_option(
                "user2",
                option_type=6,
                description="Second Additional user",
                required=False,
            ),
            create_option(
                "image",
                option_type=11,
                description="Optional image to include",
                required=False,
            ),
        ],
    )
    async def log(
        self,
        ctx: SlashContext,
        habit_name: str,
        type: str,
        user1: discord.User = None,
        user2: discord.User = None,
        image: discord.Attachment = None,
    ) -> None:
        """
        Add the log of a user completing an event
        """
        all_users = [ctx.author, user1, user2]

        habit = await config.db["habits"].find_one(
            {"guild_id": ctx.guild.id, "name": habit_name}
        )
        if not habit or not habit.get("started"):
            await ctx.send("Habit not found or not started.", hidden=True)
            return

        # Check if activity_type is valid
        allowed_types = habit.get("types", [])
        if type.lower() not in [t.lower() for t in allowed_types]:
            await ctx.send(
                f"Invalid activity type! Allowed types are: {', '.join(allowed_types)}",
                hidden=True,
            )
            return
        for user in all_users:
            if user is None:
                break
            if user.id not in habit["users"]:
                await ctx.send(
                    "One or more users are nota  part of this habit", hidden=True
                )
                return

        logged_user_ids = set()

        for user in all_users:
            if user is None:
                continue
            if user.id in logged_user_ids:
                continue

            update = {
                "$inc": {
                    f"log_periods.current.users.{user.id}.count": 1,
                    f"log_periods.current.users.{user.id}.types.{type}": 1,
                }
            }
            await config.db["habits"].update_one({"_id": habit["_id"]}, update)
            logged_user_ids.add(user.id)

        if logged_user_ids:
            mentions = ", ".join(f"<@{user_id}>" for user_id in logged_user_ids)
            content = (
                f"Logged {type} for '{habit_name}' for the following users: {mentions}!"
            )
            attachment_id = image  # image is just an int right now

            # Get the attachment object from the raw interaction
            attachments = ctx.data.get("resolved", {}).get("attachments", {})

            # If there is an image we want to just output it back to the user
            # TODO: Fix when we change over to other discord lbrirary
            if attachment_id and str(attachment_id) in attachments:
                attachment_data = attachments[str(attachment_id)]
                url = attachment_data["url"]

                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            await ctx.send("Failed to fetch the image.", hidden=True)
                            return
                        data = io.BytesIO(await resp.read())
                        file = discord.File(data, filename=attachment_data["filename"])
                        await ctx.send(content=content, file=file)
            else:
                await ctx.send(content)
        else:
            await ctx.send("No valid users to log activity for.")

    @cog_ext.cog_slash(
        name="list_habits",
        description="List all currently active habits in this server.",
    )
    async def list_habits(self, ctx: SlashContext) -> None:
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("This is an admin-only command")
            return
        """Self explnatory list all the habits that are created in your guild"""
        logging.debug(f"Listing all active habits. Guild ID: {ctx.guild.id}")
        habits_col = config.db["habits"]
        guild_habits = habits_col.find({"guild_id": ctx.guild.id})

        habits_embed = discord.Embed(title="Active Habits")
        count = 0

        async for habit in guild_habits:
            count += 1
            types = habit.get("types", [])
            types_str = ", ".join(types) if types else "None"
            started_str = "Yes" if habit.get("started") else "No"
            habit_desc = (
                f"Goal: {habit.get('goal', 'N/A')} | Frequency: {habit.get('frequency', 'N/A')}\n"
                f"Types: {types_str} | Started: {started_str}"
            )
            if "channel_id" in habit:
                habit_desc += f"\nChannel: <#{habit['channel_id']}>"
            habits_embed.add_field(
                name=f"{count}. {habit['name']}",
                value=habit_desc,
                inline=False,
            )

        if count == 0:
            habits_embed.description = "None"

        await ctx.send(embed=habits_embed)

    @cog_ext.cog_slash(
        name="delete_habit",
        description="Delete a habit by name",
        options=[
            create_option(
                name="habit_name",
                description="The name of the habit to delete",
                option_type=3,  # 3 means string
                required=True,
            )
        ],
    )
    async def delete_habit(self, ctx: SlashContext, habit_name: str) -> None:
        """Self explnatory, delete by habit name"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("This is an admin-only command")
            return
        habits_col = config.db["habits"]
        guild_id = ctx.guild.id

        result = await habits_col.delete_one({"guild_id": guild_id, "name": habit_name})

        if result.deleted_count == 1:
            await ctx.send(f"✅ Habit '{habit_name}' has been deleted.")
        else:
            await ctx.send(f"❌ No habit found with the name '{habit_name}'.")

    async def update_habits(self, ctx):
        """
        This runs the checker to see if we've reached the endtime for any of the current habit periods,
        if so then it outputs the tables to showcase the updates to the standings
        """
        now = datetime.now(pytz.utc)
        habits = config.db["habits"].find({"started": True})
        async for habit in habits:
            end = datetime.fromisoformat(habit["log_periods"]["current"]["end"])
            if now >= end:
                guild = self.bot.get_guild(habit.get("guild_id"))
                channel = self.bot.get_channel(habit.get("channel_id"))
                habit["total"] = self.update_totals(habit)
                start_new, end_new = self.get_period_bounds(habit["frequency"])

                empty_types = {act_type: 0 for act_type in habit["types"]}
                current_users = {
                    str(user_id): {"types": empty_types.copy(), "count": 0}
                    for user_id in habit["users"]
                }

                habit["log_periods"]["current"] = {
                    "start": start_new.isoformat(),
                    "end": end_new.isoformat(),
                    "users": current_users,
                }

                await config.db["habits"].replace_one({"_id": habit["_id"]}, habit)

                if channel:
                    user_mentions = " ".join(
                        f"<@{user_id}>" for user_id in habit.get("users", [])
                    )

                    # Generate the weekly summary, construct message, then send to channel
                    self.generate_weekly_summary_image(guild, habit)

                    current_period_summary_header = (
                        f"# {habit['name']} Summary ({habit['frequency']})\n"
                    )
                    habit_participants = f"Participants: {user_mentions}"
                    current_period_summary_message = (
                        current_period_summary_header + habit_participants
                    )
                    await channel.send(
                        content=current_period_summary_message,
                        file=discord.File("habit_summary.png"),
                    )
                    if os.path.exists("habit_summary.png"):
                        os.remove("habit_summary.png")

                    # Same as above for total summary
                    self.generate_total_summary_image(guild, habit)
                    totals_message = f"# Totals for habit {habit['name']} \n"
                    await channel.send(
                        content=totals_message,
                        file=discord.File("totals_table.png"),
                    )
                    if os.path.exists("totals_table.png"):
                        os.remove("totals_table.png")

                else:
                    logging.error("Channel not found for habit: %s", habit["name"])


def setup(bot):
    bot.add_cog(HabitTrackerCog(bot))
