"""
Smart Office Monitor — Alert Engine

Evaluates two rules after every device state change:
  1. Office-hours rule  — any device ON outside 09:00–17:00
  2. Long-running rule   — every device in one room ON for > threshold
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from backend.config import (
    ROOMS,
    OFFICE_HOURS_START,
    OFFICE_HOURS_END,
    LONG_RUNNING_THRESHOLD_SECONDS,
)
from backend import database as db
from backend.models import Alert, Severity

logger = logging.getLogger(__name__)

_discord_alert_callback: Callable[..., Coroutine[Any, Any, None]] | None = None


def set_discord_alert_callback(callback: Callable) -> None:
    global _discord_alert_callback
    _discord_alert_callback = callback


# ── Public entry point ────────────────────────────────────────────────────────

async def check_all_alerts() -> None:
    """Run every alert rule."""
    await _check_office_hours()
    await _check_long_running_rooms()


# ── Rule 1: Office-hours ──────────────────────────────────────────────────────

async def _check_office_hours() -> None:
    now = datetime.now()

    if OFFICE_HOURS_START <= now.hour < OFFICE_HOURS_END:
        # Within office hours → auto-resolve stale after-hours alerts
        for room in ROOMS:
            db.resolve_alerts_for_condition(room, "after office hours")
        return

    # Outside office hours — flag every ON device
    for room in ROOMS:
        on_devices = [d for d in db.get_devices_by_room(room) if d.status]
        if on_devices:
            names = ", ".join(d.name for d in on_devices)
            message = (
                f"{room}: {len(on_devices)} device(s) still ON after office hours "
                f"— {names}"
            )
            alert = Alert(
                id=str(uuid.uuid4()),
                message=message,
                timestamp=datetime.now(timezone.utc),
                room=room,
                severity=Severity.WARNING,
            )
            added = db.add_alert(alert)
            if added:
                logger.info("🔔 Alert: %s", message)
                if _discord_alert_callback:
                    await _discord_alert_callback(alert)
        else:
            db.resolve_alerts_for_condition(room, "after office hours")


# ── Rule 2: Long-running room ────────────────────────────────────────────────

async def _check_long_running_rooms() -> None:
    now = datetime.now(timezone.utc)

    for room in ROOMS:
        room_devices = db.get_devices_by_room(room)
        if not room_devices:
            continue

        all_on = all(d.status for d in room_devices)

        if all_on:
            oldest = min(d.last_changed for d in room_devices)
            duration = (now - oldest).total_seconds()

            if duration >= LONG_RUNNING_THRESHOLD_SECONDS:
                hours = round(duration / 3600, 1)
                message = (
                    f"{room}: All devices have been ON for {hours}+ hours"
                )
                alert = Alert(
                    id=str(uuid.uuid4()),
                    message=message,
                    timestamp=datetime.now(timezone.utc),
                    room=room,
                    severity=Severity.CRITICAL,
                )
                added = db.add_alert(alert)
                if added:
                    logger.info("🚨 Alert: %s", message)
                    if _discord_alert_callback:
                        await _discord_alert_callback(alert)
        else:
            db.resolve_alerts_for_condition(room, "All devices have been ON")
