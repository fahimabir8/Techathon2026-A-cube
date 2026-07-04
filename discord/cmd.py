from discord.ext import commands
from bot import UsageBot
import os
from dotenv import load_dotenv

load_dotenv()
BACKEND_API = os.getenv("BACKEND_API")


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
                ai_resp = await self.bot.ai_handler.humanize("status", data)
                await fmsg.edit(content=ai_resp["message"])
        except Exception as e:
            await fmsg.edit(content=f"error: {e}")


async def setup(bot: UsageBot):
    await bot.add_cog(CmdCog(bot))
