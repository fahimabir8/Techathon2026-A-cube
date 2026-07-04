import discord
from discord.ext import commands
from bot import UsageBot
import os
from dotenv import load_dotenv

load_dotenv()
BACKEND_API = os.getenv("BACKEND_API")
AI_CHANNEL_ID = os.getenv("AI_CHANNEL_ID")


class CmdCog(commands.Cog):
    def __init__(self, bot: UsageBot) -> None:
        self.bot = bot
        super().__init__()

    @commands.command()
    async def status(self, ctx: commands.Context):
        fmsg = await ctx.send("getting status")
        try:
            async with self.bot.web_session.get(f"{BACKEND_API}/rooms") as resp:
                resp.raise_for_status()
                data = await resp.json()
                await fmsg.edit(content="humanizing")
                ai_resp = await self.bot.ai_handler.humanize("status", data)
                print(type(ai_resp))
                await fmsg.edit(content=ai_resp["message"])
        except Exception as e:
            await fmsg.edit(content=f"error: {e}")

    @commands.command()
    async def room(self, ctx: commands.Context, room: str):
        fmsg = await ctx.send("getting data")
        try:
            async with self.bot.web_session.get(f"{BACKEND_API}/room/{room}") as resp:
                resp.raise_for_status()
                data = await resp.json()
                await fmsg.edit(content="humanizing")
                ai_resp = await self.bot.ai_handler.humanize("room", data)
                await fmsg.edit(content=ai_resp["message"])
        except Exception as e:
            await fmsg.edit(content=f"error: {e}")

    @commands.command()
    async def usage(self, ctx: commands.Context):
        fmsg = await ctx.send("getting status")
        try:
            async with self.bot.web_session.get(f"{BACKEND_API}/power") as resp:
                resp.raise_for_status()
                data = await resp.json()
                await fmsg.edit(content="humanizing")
                ai_resp = await self.bot.ai_handler.humanize("usage", data)
                await fmsg.edit(content=ai_resp["message"])
        except Exception as e:
            await fmsg.edit(content=f"error: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        print("message")
        if message.author.bot:
            print("bot")
            return
        if message.channel.id != int(AI_CHANNEL_ID):
            print("not channel", message.channel.id)
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return
        print("running ai")
        try:
            intent = await self.bot.ai_handler.get_intent(message.content)
        except Exception as e:
            await message.reply(f"error: {e}")

        command_name = intent.get("command")
        room = intent.get("room")
        command = self.bot.get_command(command_name)
        if command is None:
            await message.reply("couldn't figure out what you are asking")
            return

        try:
            if command_name == "room":
                if not room:
                    await message.reply("no room specified")
                    return
                await ctx.invoke(command, room=room)
            else:
                await ctx.invoke(command)
        except Exception as e:
            await message.reply(f"error running command: {e}")


async def setup(bot: UsageBot):
    await bot.add_cog(CmdCog(bot))
