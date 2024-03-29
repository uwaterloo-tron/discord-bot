"""
Modified from https://gist.github.com/vbe0201/ade9b80f2d3b64643d854938d40a0a2d
"""
import asyncio
import functools
import itertools
import logging
import math
import random
import discord
import youtube_dl
from async_timeout import timeout
from discord.ext import commands

# Silence useless bug reports messages
import config

youtube_dl.utils.bug_reports_message = lambda: ""


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        "format": "bestaudio/best",
        "extractaudio": True,
        "audioformat": "mp3",
        "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
        "source_address": "0.0.0.0",
    }

    FFMPEG_OPTIONS = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn",
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(
        self,
        ctx: commands.Context,
        source: discord.FFmpegPCMAudio,
        *,
        data: dict,
        volume: float = 1.0,  # Default volume: 100%
    ):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get("uploader")
        self.uploader_url = data.get("uploader_url")
        date = data.get("upload_date")
        self.upload_date = date[6:8] + "." + date[4:6] + "." + date[0:4]
        self.title = data.get("title")
        self.thumbnail = data.get("thumbnail")
        self.description = data.get("description")
        self.duration = self.parse_duration(int(data.get("duration")))
        self.tags = data.get("tags")
        self.url = data.get("webpage_url")
        self.views = data.get("view_count")
        self.likes = data.get("like_count")
        self.dislikes = data.get("dislike_count")
        self.stream_url = data.get("url")

    def __str__(self):
        return f"**{self.title}** by **{self.uploader}**"

    @classmethod
    async def get_playlist_songs(
        cls,
        ctx: commands.Context,
        loop: asyncio.BaseEventLoop,
        search: str,
        entries,
    ):
        ctx.voice_state.songs.queueing = True
        found_vid = False
        for entry in entries:
            if entry:
                found_vid = True
                partial = functools.partial(
                    cls.ytdl.extract_info, entry["id"], download=False
                )
                max_retries = 5
                for i in range(1, max_retries - 1):
                    try:
                        processed_info = await loop.run_in_executor(None, partial)
                        if processed_info is None:
                            continue
                    except youtube_dl.DownloadError as e:
                        if (
                            str(e)
                            == "ERROR: Sign in to confirm your age\nThis video may be inappropriate for some users."
                        ):
                            embed = discord.Embed(
                                title="",
                                description=f"The following song is age-restricted, so it cannot be played:\n"
                                f"**[{entry['title']}](https://www.youtube.com/watch?v={entry['id']})**",
                                color=discord.Color.red(),
                            )
                            await ctx.send(embed=embed)
                            break
                        else:
                            logging.error(str(e))
                    else:
                        source = await cls.song_source(ctx, processed_info, search)
                        if source is None:
                            raise YTDLError(
                                "processed_info for playlist song contained 'entries' field with 0 elements."
                            )

                        if not ctx.voice_state.songs.queueing:
                            return

                        await ctx.voice_state.songs.put(source)
                        break

                    logging.error(f"Failed to get song: attempt {i}/{max_retries}")
                else:
                    embed = discord.Embed(
                        title="",
                        description=f"Failed to enqueue the following song (max attempts reached), skipping:\n"
                        f"**[{entry['title']}](https://www.youtube.com/watch?v={entry['id']})**",
                        color=discord.Color.red(),
                    )
                    await ctx.send(embed=embed)

        if not found_vid:
            embed = discord.Embed(
                title="",
                description=f"Couldn't find anything that matches `{search}`",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @classmethod
    async def song_source(
        cls, ctx: commands.Context, processed_info: dict, search: str
    ):
        if "entries" not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info["entries"].pop(0)
                except IndexError:
                    embed = discord.Embed(
                        title="",
                        description=f"Couldn't find anything that matches `{search}`",
                        color=discord.Color.red(),
                    )
                    await ctx.send(embed=embed)
                    return None

        source = {
            "ctx": ctx,
            "data": info,
        }

        return source

    @classmethod
    async def create_source(
        cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None
    ):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(
            cls.ytdl.extract_info, search, download=False, process=False
        )

        max_retries = 5
        for i in range(1, max_retries - 1):
            try:
                data = await loop.run_in_executor(None, partial)
            except youtube_dl.DownloadError as e:
                if (
                    str(e)
                    == "ERROR: Sign in to confirm your age\nThis video may be inappropriate for some users."
                ):
                    embed = discord.Embed(
                        title="",
                        description="This song is age-restricted, so it cannot be played.",
                        color=discord.Color.red(),
                    )
                    return await ctx.send(embed=embed)
                else:
                    logging.error(str(e))
            else:
                break
            logging.error(f"Failed to get song: attempt {i}/{max_retries}")
        else:
            embed = discord.Embed(
                title="",
                description=f"Failed to enqueue this song (max attempts reached).",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            raise YTDLError("Failed to find song")

        if data is None:
            embed = discord.Embed(
                title="",
                description=f"Couldn't find anything that matches `{search}`",
                color=discord.Color.red(),
            )
            return await ctx.send(embed=embed)

        if "entries" not in data:
            process_info = data

            webpage_url = process_info["webpage_url"]
            partial = functools.partial(
                cls.ytdl.extract_info, webpage_url, download=False
            )
            for i in range(1, max_retries - 1):
                processed_info = await loop.run_in_executor(None, partial)
                if processed_info is not None:
                    break
            else:
                embed = discord.Embed(
                    title="",
                    description=f"Couldn't find anything that matches `{search}`",
                    color=discord.Color.red(),
                )
                return await ctx.send(embed=embed)

            source = await cls.song_source(ctx, processed_info, search)
            if source is None:
                return
            await ctx.voice_state.songs.put(source)
            embed = discord.Embed(
                title="",
                description=f"Enqueued {source['data']['title']}",
                color=discord.Color.blurple(),
            )
            await ctx.send(embed=embed)

        else:
            embed = discord.Embed(
                title="",
                description=f"Enqueueing playlist **{data['title']}**",
                color=discord.Color.blurple(),
            )
            await ctx.send(embed=embed)
            ctx.bot.loop.create_task(
                cls.get_playlist_songs(ctx, loop, search, data["entries"])
            )

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append(f"{days} days")
        if hours > 0:
            duration.append(f"{hours} hours")
        if minutes > 0:
            duration.append(f"{minutes} minutes")
        if seconds > 0:
            duration.append(f"{seconds} seconds")

        return ", ".join(duration)


class Song:
    __slots__ = ("source", "requester")

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        duration = self.source.duration if self.source.duration else "∞ (livestream)"

        embed = (
            discord.Embed(
                title="Now playing",
                description=f"```css\n{self.source.title}\n```",
                color=discord.Color.blurple(),
            )
            .add_field(name="Duration", value=duration)
            .add_field(name="Requested by", value=self.requester.mention)
            .add_field(
                name="Uploader",
                value=f"[{self.source.uploader}]({self.source.uploader_url})",
            )
            .add_field(name="URL", value=f"[Click]({self.source.url})")
            .set_thumbnail(url=self.source.thumbnail)
        )

        return embed


class SongQueue(asyncio.Queue):
    queueing = False

    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()
        self.queueing = False

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 1.0  # Default volume: 100%
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(60 * 3):  # 3 minutes
                        source = await self.songs.get()
                        ffmpeg = discord.FFmpegPCMAudio(
                            source["data"]["url"], **YTDLSource.FFMPEG_OPTIONS
                        )
                        self.current = Song(
                            YTDLSource(source["ctx"], ffmpeg, data=source["data"])
                        )
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    # This will cause the bot to poll infinitely. This should be improved.
                    continue

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()
            self.current = None
            self.songs.task_done()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()
        self.current = None

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage(
                "This command can't be used in DM channels."
            )

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    @commands.command(name="join", invoke_without_subcommand=True)
    async def _join(
        self, ctx: commands.Context, *, channel: discord.VoiceChannel = None
    ):
        """
        Summons the bot to a voice channel.
        If no channel was specified, it joins your channel.

        :param channel: The voice channel you want the bot to join. [Optional]
        """

        if not channel and not ctx.author.voice:
            embed = discord.Embed(
                title="",
                description=f"You must be in a voice channel to summon me.\n"
                f"You can also tell me where to go with `{await config.get_prefix(ctx.guild)}join VoiceChannelName`.",
                color=discord.Color.red(),
            )
            return await ctx.send(embed=embed)

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            # Pause music before joining another channel (otherwise the song freezes)
            was_playing = False
            if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
                ctx.voice_state.voice.pause()
                was_playing = True

            await asyncio.sleep(0.5)
            await ctx.voice_state.voice.move_to(destination)
            await asyncio.sleep(0.5)

            # Resume playing the music after joining if it was playing when the command was called.
            # If paused while it was called, stay paused.
            if was_playing and ctx.voice_state.voice.is_paused():
                ctx.voice_state.voice.resume()
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name="leave", aliases=["disconnect"])
    async def _leave(self, ctx: commands.Context):
        """
        Clears the queue and leaves the voice channel.
        """

        if not ctx.voice_state.voice:
            embed = discord.Embed(
                title="",
                description="Not connected to any voice channel.",
                color=discord.Color.blurple(),
            )
            return await ctx.send(embed=embed)

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(name="volume", aliases=["vol", "v"])
    async def _volume(self, ctx: commands.Context, *, volume: int = None):
        """
        Sets the volume of the player.
        If no value is provided, displays the current volume of the player.

        :param volume: The new volume of the music player, can be 0-100. [Optional]
        """

        if volume is None:
            embed = discord.Embed(
                title="",
                description=f"🔊 **{ctx.voice_state.current.source.volume * 100}%**",
                color=discord.Color.green(),
            )
            return await ctx.send(embed=embed)

        if volume < 0 or volume > 100:
            embed = discord.Embed(
                title="",
                description="Please enter a value between 0 and 100",
                color=discord.Color.red(),
            )
            return await ctx.send(embed=embed)

        if ctx.voice_state.is_playing:
            ctx.voice_state.current.source.volume = volume / 100
        ctx.voice_state.volume = volume / 100
        embed = discord.Embed(
            title="",
            description=f"🔊 {ctx.author.mention} set the volume to **{volume}%**",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="now", aliases=["current", "playing"])
    async def _now(self, ctx: commands.Context):
        """
        Displays the currently playing song.
        """
        if ctx.voice_state.current is None:
            embed = discord.Embed(
                title="",
                description="Nothing playing right now",
                color=discord.Color.blurple(),
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(embed=ctx.voice_state.current.create_embed())

    @commands.command(name="pause")
    async def _pause(self, ctx: commands.Context):
        """
        Pauses the currently playing song.
        """

        if not ctx.voice_state.voice:
            embed = discord.Embed(
                title="",
                description="Not connected to any voice channel.",
                color=discord.Color.blurple(),
            )
            return await ctx.send(embed=embed)

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction("⏯")

    @commands.command(name="resume")
    async def _resume(self, ctx: commands.Context):
        """
        Resumes a currently paused song.
        """

        if not ctx.voice_state.voice:
            embed = discord.Embed(
                title="",
                description="Not connected to any voice channel.",
                color=discord.Color.blurple(),
            )
            return await ctx.send(embed=embed)

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction("⏯")

    @commands.command(name="clear", aliases=["cl"])
    async def _clear(self, ctx: commands.Context):
        """
        Clears the queue.
        """

        ctx.voice_state.songs.clear()
        await ctx.message.add_reaction("⏏")

    @commands.command(name="skip")
    async def _skip(self, ctx: commands.Context):
        """
        Vote to skip a song. The requester and admins can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            embed = discord.Embed(
                title="",
                description="Not playing any music right now...",
                color=discord.Color.blurple(),
            )
            return await ctx.send(embed=embed)

        voter = ctx.message.author
        if (
            voter == ctx.voice_state.current.requester
            or voter.guild_permissions.administrator
        ):
            await ctx.message.add_reaction("⏭")
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.message.add_reaction("⏭")
                ctx.voice_state.skip()
            else:
                embed = discord.Embed(
                    title="",
                    description=f"Skip vote added, currently at **{total_votes}/3**",
                    color=discord.Color.green(),
                )
                await ctx.send(embed=embed)

        else:
            embed = discord.Embed(
                title="",
                description="You have already voted to skip this song.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command(name="queue", aliases=["que", "q"])
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """
        Shows the player's queue.
        You can optionally specify the page to show. Each page contains 10 elements.

        :param page: The page of the queue you want to show. [Optional]
        """

        if len(ctx.voice_state.songs) == 0:
            embed = discord.Embed(
                title="",
                description="Empty queue.",
                color=discord.Color.blurple(),
            )
            return await ctx.send(embed=embed)

        if page > len(ctx.voice_state.songs) or page < 1:
            embed = discord.Embed(
                title="",
                description="Invalid page number.",
                color=discord.Color.red(),
            )
            return await ctx.send(embed=embed)

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ""
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += f"`{i + 1}.` [**{song['data']['title']}**]({song['data']['webpage_url']})\n"

        embed = discord.Embed(
            description=f"**{len(ctx.voice_state.songs)} tracks:**\n\n{queue}"
        ).set_footer(text=f"Viewing page {page}/{pages}")
        await ctx.send(embed=embed)

    @commands.command(name="shuffle")
    async def _shuffle(self, ctx: commands.Context):
        """
        Shuffles the queue.
        """

        if len(ctx.voice_state.songs) == 0:
            embed = discord.Embed(
                title="",
                description="Empty queue.",
                color=discord.Color.blurple(),
            )
            return await ctx.send(embed=embed)

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction("✅")

    @commands.command(name="remove")
    async def _remove(self, ctx: commands.Context, index: int):
        """
        Removes a song from the given position in the queue.

        :param index: The position of the song in queue to be removed.
        """

        if len(ctx.voice_state.songs) == 0:
            embed = discord.Embed(
                title="",
                description="Empty queue.",
                color=discord.Color.blurple(),
            )
            return await ctx.send(embed=embed)

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction("✅")

    @commands.command(name="loop")
    async def _loop(self, ctx: commands.Context):
        """
        Loops the currently playing song.
        Invoke this command again to unloop the song.
        """

        if not ctx.voice_state.is_playing:
            embed = discord.Embed(
                title="",
                description="Nothing being played at the moment.",
                color=discord.Color.blurple(),
            )
            return await ctx.send(embed=embed)

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.message.add_reaction("✅")

    @commands.command(name="play")
    async def _play(self, ctx: commands.Context, *, search: str = None):
        """
        Plays a song.
        If there are songs in the queue, this will be queued until the
        other songs finished playing.
        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html

        :param search: The song that you want to play.
        """
        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(
                title="",
                description="You are not connected to any voice channel.",
                color=discord.Color.red(),
            )
            return await ctx.send(embed=embed)

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                embed = discord.Embed(
                    title="",
                    description="You must be in the same voice channel as me.",
                    color=discord.Color.red(),
                )
                return await ctx.send(embed=embed)

        if search is None:
            return await self._resume(ctx)

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            await YTDLSource.create_source(ctx, search, loop=self.bot.loop)


def setup(bot):
    # Adds cog to bot from main.py
    bot.add_cog(MusicCog(bot))
