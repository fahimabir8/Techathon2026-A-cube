from discord.ext import commands
from discord import Intents

import aiohttp
import os
from dotenv import load_dotenv
from ai import AiHandler

load_dotenv()
TOKEN = os.getenv("TOKEN")
assert TOKEN


class UsageBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",
            intents=Intents.all(),
        )

    async def setup_hook(self) -> None:
        self.web_session = aiohttp.ClientSession()
        self.ai_handler = AiHandler(self.web_session)
        await self.load_extension("cmd")
        await self.load_extension("alert")
        return await super().setup_hook()

    async def close(self) -> None:
        if self.web_session:
            await self.web_session.close()
        await super().close()


if __name__ == "__main__":
    UsageBot().run(TOKEN)
