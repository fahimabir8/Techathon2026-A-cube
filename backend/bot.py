"""
Smart Office Monitor — Discord Bot

Commands:
  !status  — office-wide device summary
  !room <name> — single-room detail
  !usage   — current power & estimated daily kWh

Also auto-posts alerts to a configured channel (DISCORD_CHANNEL_ID).
"""

import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands

from backend.config import (
    DISCORD_TOKEN,
    DISCORD_CHANNEL_ID,
    DISCORD_COMMAND_PREFIX,
    ROOMS,
)
from backend import database as db
from backend.models import Alert, DeviceType
from backend.alerts import set_discord_alert_callback

logger = logging.getLogger(__name__)

# ── Bot setup ─────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=DISCORD_COMMAND_PREFIX,
    intents=intents,
    help_command=commands.DefaultHelpCommand(),
)

_alert_channel: discord.TextChannel | None = None


# ── Events ────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    global _alert_channel
    logger.info("🤖 Discord bot logged in as %s", bot.user)

    if DISCORD_CHANNEL_ID:
        try:
            _alert_channel = bot.get_channel(int(DISCORD_CHANNEL_ID))
            if _alert_channel:
                logger.info("   Alert channel: #%s", _alert_channel.name)
        except ValueError:
            logger.warning("   Invalid DISCORD_CHANNEL_ID: %s", DISCORD_CHANNEL_ID)


# ── Commands ──────────────────────────────────────────────────────────────────

@bot.command(name="status")
async def cmd_status(ctx: commands.Context):
    """Show a summary of every room."""
    embed = discord.Embed(
        title="🏢 Office Device Status",
        colour=0x3B82F6,
        timestamp=datetime.now(timezone.utc),
    )

    for room in ROOMS:
        devs      = db.get_devices_by_room(room)
        fans_on   = len([d for d in devs if d.type == DeviceType.FAN   and d.status])
        fans_tot  = len([d for d in devs if d.type == DeviceType.FAN])
        lights_on = len([d for d in devs if d.type == DeviceType.LIGHT and d.status])
        lights_tot= len([d for d in devs if d.type == DeviceType.LIGHT])
        power     = sum(d.power_draw for d in devs if d.status)

        lines: list[str] = []
        if fans_on == 0 and lights_on == 0:
            lines.append("All devices OFF")
        else:
            lines.append(f"🌀 {fans_on}/{fans_tot} fans ON")
            lines.append(f"💡 {lights_on}/{lights_tot} lights ON")
        lines.append(f"⚡ {power:.1f}W")

        embed.add_field(name=f"📍 {room}", value="\n".join(lines), inline=True)

    await ctx.send(embed=embed)


_ROOM_MAP: dict[str, str] = {
    "drawing":      "Drawing Room",
    "drawing room": "Drawing Room",
    "work1":        "Work Room 1",
    "work room 1":  "Work Room 1",
    "work2":        "Work Room 2",
    "work room 2":  "Work Room 2",
}


@bot.command(name="room")
async def cmd_room(ctx: commands.Context, *, room_name: str | None = None):
    """Show details for a specific room (e.g. `!room work1`)."""
    if not room_name:
        await ctx.send(
            "❌ Please specify a room: `!room drawing`, `!room work1`, `!room work2`"
        )
        return

    normalised = _ROOM_MAP.get(room_name.lower().strip())
    if not normalised:
        await ctx.send(
            f"❌ Room `{room_name}` not found.\n"
            f"Available: `drawing`, `work1`, `work2`"
        )
        return

    devs = db.get_devices_by_room(normalised)

    embed = discord.Embed(
        title=f"📍 {normalised}",
        colour=0x10B981,
        timestamp=datetime.now(timezone.utc),
    )

    for d in devs:
        icon   = "🌀" if d.type == DeviceType.FAN else "💡"
        status = "🟢 ON" if d.status else "🔴 OFF"
        power  = f"{d.power_draw:.1f}W" if d.status else "0W"
        embed.add_field(name=f"{icon} {d.name}", value=f"{status} | {power}", inline=True)

    total = sum(d.power_draw for d in devs if d.status)
    embed.set_footer(text=f"Total Power: {total:.1f}W")

    await ctx.send(embed=embed)


@bot.command(name="usage")
async def cmd_usage(ctx: commands.Context):
    """Show current power draw and estimated daily consumption."""
    pwr = db.get_power_summary()

    embed = discord.Embed(
        title="⚡ Power Usage Report",
        colour=0xF59E0B,
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Current Total", value=f"**{pwr['total_power']:.1f}W**", inline=True)
    embed.add_field(
        name="Est. Daily Usage",
        value=f"**{pwr['estimated_daily_kwh']:.2f} kWh**",
        inline=True,
    )

    room_lines = [f"📍 {r}: **{w:.1f}W**" for r, w in pwr["rooms"].items()]
    embed.add_field(
        name="Room Breakdown",
        value="\n".join(room_lines) or "No data",
        inline=False,
    )

    await ctx.send(embed=embed)


# ── Auto-post alerts ──────────────────────────────────────────────────────────

async def _post_alert(alert: Alert) -> None:
    """Forward an alert to the configured Discord channel."""
    if not _alert_channel:
        return

    emoji_map = {"warning": "⚠️", "critical": "🚨", "info": "ℹ️"}
    emoji = emoji_map.get(alert.severity, "⚠️")

    embed = discord.Embed(
        title=f"{emoji} Alert: {alert.severity.value.upper()}",
        description=alert.message,
        colour=0xEF4444 if alert.severity == "critical" else 0xF59E0B,
        timestamp=alert.timestamp,
    )
    embed.add_field(name="Room", value=alert.room, inline=True)
    embed.add_field(
        name="Time",
        value=alert.timestamp.strftime("%I:%M %p"),
        inline=True,
    )

    try:
        await _alert_channel.send(embed=embed)
    except Exception:
        logger.exception("Failed to post alert to Discord")


# ── Entrypoint ────────────────────────────────────────────────────────────────

async def start_bot() -> None:
    """Called from the FastAPI lifespan as an asyncio task."""
    set_discord_alert_callback(_post_alert)
    try:
        await bot.start(DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.error("Invalid Discord token — bot will not run")
    except Exception:
        logger.exception("Discord bot error")
