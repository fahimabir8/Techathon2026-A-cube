from datetime import datetime, timezone
from bot import UsageBot
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv

load_dotenv()

ALERT_CHANNEL_ID = os.getenv("ALERT_CHANNEL_ID")
BACKEND_API = os.getenv("BACKEND_API")


class Alerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # first run: only show alerts from now onward
        self.last_alert_time = self._now_iso()
        self.alert_loop.start()

    async def cog_unload(self):
        self.alert_loop.cancel()

    @staticmethod
    def _now_iso():
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000000Z")

    async def _fetch_new_alerts(self):
        """Hits /api/alerts with start=last_alert_time. Raises on HTTP error."""
        async with self.bot.web_session.get(
            f"{BACKEND_API}/alerts", params={"start": self.last_alert_time}
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    @tasks.loop(minutes=5)
    async def alert_loop(self):
        channel = self.bot.get_channel(ALERT_CHANNEL_ID)
        if channel is None:
            return
        try:
            data = await self._fetch_new_alerts()
        except Exception as e:
            await channel.send(f"error: {e}")
            return

        if not data:
            return  # no alerts, no message, don't touch last_alert_time

        try:
            ai_resp = await self.bot.ai_handler.humanize("alert", data)
            await channel.send(ai_resp["message"])
            self.last_alert_time = self._now_iso()
        except Exception as e:
            await channel.send(f"error: {e}")

    @alert_loop.before_loop
    async def before_alert_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: UsageBot):
    await bot.add_cog(Alerts(UsageBot()))
