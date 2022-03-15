import discord
from discord.ext import tasks, commands
import config
import io
import os
import aiohttp
import math
import pyheif
import sys
from PIL import Image
from pdf2image import convert_from_bytes, pdfinfo_from_bytes
from typing import Optional


async def save_jpg_with_target_size(
    im: Image, filename: io.BytesIO, target: int
) -> Optional[io.BytesIO]:
    # https://stackoverflow.com/questions/52259476/how-to-reduce-a-jpeg-size-to-a-desired-size/52281257#52281257
    """Save the image as JPEG with the given name at best quality that makes less than "target" bytes"""
    # Min and Max quality
    Qmin, Qmax = 25, 96
    # Highest acceptable quality found
    Qacc = -1
    while Qmin <= Qmax:
        m = math.floor((Qmin + Qmax) / 2)

        # Encode into memory and get size
        buffer = io.BytesIO()
        im.save(buffer, format="JPEG", quality=m)
        s = buffer.getbuffer().nbytes

        if s <= target:
            Qacc = m
            Qmin = m + 1
        elif s > target:
            Qmax = m - 1

    # Write to disk at the defined quality
    if Qacc > -1:
        im.save(filename, format="JPEG", quality=Qacc)
        filename.seek(0)
        return filename
    else:
        print("ERROR: No acceptable quality factor found", file=sys.stderr)
        return None


class FileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Listens for messages with specific file types and does actions depending on the file type sent"""
        # ignore messages without attachments
        if message.author == self.bot.user or len(message.attachments) == 0:
            return
        added_pdf = False
        for attachment in message.attachments:
            # handles case of multiple pdf attachments
            if not added_pdf and any(
                attachment.filename.endswith(i) for i in [".pdf", ".PDF"]
            ):
                yimin_emote = self.bot.get_emoji(733516365243220038)
                await message.add_reaction(yimin_emote)
                added_pdf = True
            elif any(attachment.filename.endswith(i) for i in [".heic", ".HEIC"]):
                # Download PDF from Discord CDN
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as r:
                        file = io.BytesIO(await r.read())
                # read the file
                heif_file = pyheif.read(file)
                image = Image.frombytes(
                    heif_file.mode,
                    heif_file.size,
                    heif_file.data,
                    "raw",
                    heif_file.mode,
                    heif_file.stride,
                )
                with io.BytesIO() as image_binary:
                    # Discord has a max upload size of 8MB,
                    # so reduce image file size to 8MB.
                    image_binary = await save_jpg_with_target_size(
                        image, image_binary, 8e6
                    )
                    if image_binary is None:
                        await message.channel.send("`ERROR: failed to resize image`")

                    await message.channel.send(
                        file=discord.File(
                            fp=image_binary, filename=attachment.filename[:-5] + ".png"
                        )
                    )

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        """Listens for a specific reaction on a file type and sends that file in a pre-viewable manner"""
        yimin_emote = self.bot.get_emoji(733516365243220038)
        if payload.user_id == self.bot.user.id or payload.emoji != yimin_emote:
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if message.attachments == 0:
            return
        # Hard-coded value that determines output image resolution
        dpi = 200  # dots per inch
        for attachment in message.attachments:
            if any(attachment.filename.endswith(i) for i in [".pdf", ".PDF"]):
                print(f"Converting {attachment.filename} to images...")

                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as r:
                        pdf_file = await r.content.read()

                info = pdfinfo_from_bytes(pdf_file, userpw=None, poppler_path=None)

                max_pages = info["Pages"]
                # Hard-coded limit for the number of pages we store in memory at once.
                pages_in_mem = 1
                for pg in range(1, max_pages + 1, pages_in_mem):
                    # Convert PDF page bytes to PIL image object
                    pages = convert_from_bytes(
                        pdf_file,
                        dpi,
                        first_page=pg,
                        last_page=min(pg + pages_in_mem - 1, max_pages),
                    )
                    for idx, page in enumerate(pages):
                        # Convert PIL image object to PNG image bytes and send
                        with io.BytesIO() as image_binary:
                            page.save(image_binary, "PNG")
                            image_binary.seek(0)
                            await message.channel.send(
                                file=discord.File(
                                    fp=image_binary,
                                    filename=f"{os.path.splitext(attachment.filename)}_{idx + 1}.png",
                                )
                            )


def setup(bot):
    # Adds cog to bot from main.py
    if config.STAGE != "dev":
        # dont add this cog if we are in dev to avoid duplication, remove for testing
        bot.add_cog(FileCog(bot))
