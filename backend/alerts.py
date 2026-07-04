"""
Smart Office Monitor — Alert Engine

Evaluates two rules after every device state change:
  1. Office-hours rule  — any device ON outside 09:00–17:00
  2. Long-running rule   — every device in one room ON for > threshold
"""

import logging
import uuid
from datetime import datetime
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
#   One alert per individual device that is ON outside 09:00–17:00.
#   Message is stable per device so duplicates are impossible.

async def _check_office_hours() -> None:
    now = db.get_current_time()

    if OFFICE_HOURS_START <= now.hour < OFFICE_HOURS_END:
        # Within office hours → resolve every after-hours alert
        for room in ROOMS:
            db.resolve_alerts_for_condition(room, "after office hours")
        return

    # Outside office hours — one alert per ON device
    for room in ROOMS:
        for dev in db.get_devices_by_room(room):
            # Stable message keyed to this specific device
            msg = f"{dev.name} in {room} is ON after office hours"

            if dev.status:
                alert = Alert(
                    id=str(uuid.uuid4()),
                    message=msg,
                    timestamp=db.get_current_time(),
                    room=room,
                    severity=Severity.WARNING,
                )
                added = db.add_alert(alert)
                if added:
                    logger.info("🔔 Alert: %s", msg)
                    if _discord_alert_callback:
                        await _discord_alert_callback(alert)
            else:
                # Device is OFF → resolve its specific alert if any
                db.resolve_alerts_for_condition(room, msg)


# ── Rule 2: Long-running room (office hours only) ────────────────────────────
#   Fires when ALL devices in a room have been ON for ≥ 2 hours
#   during office hours. Uses a stable message so no duplicates.

_room_all_on_start: dict[str, datetime | None] = {}


def _office_start_utc(now_local: datetime, now_utc: datetime) -> datetime:
    office_start_local = now_local.replace(
        hour=OFFICE_HOURS_START,
        minute=0,
        second=0,
        microsecond=0,
    )
    return now_utc - (now_local - office_start_local)


async def _check_long_running_rooms() -> None:
    now_local = db.get_current_time()
    now_utc = db.get_current_utc_time()

    # Only evaluate during office hours
    if not (OFFICE_HOURS_START <= now_local.hour < OFFICE_HOURS_END):
        for room in ROOMS:
            db.resolve_alerts_for_condition(room, "All devices have been ON")
        _room_all_on_start.clear()
        return

    office_start = _office_start_utc(now_local, now_utc)

    for room in ROOMS:
        room_devices = db.get_devices_by_room(room)
        if not room_devices:
            continue

        all_on = all(d.status for d in room_devices)

        # Stable message — no changing hour count
        msg = f"{room}: All devices have been ON for 2+ hours"

        if all_on:
            all_on_since = max(d.last_changed for d in room_devices)
            timer_start = max(all_on_since, office_start)
            tracked_start = _room_all_on_start.get(room)

            if tracked_start is None or tracked_start < timer_start:
                _room_all_on_start[room] = timer_start

            duration = (now_utc - _room_all_on_start[room]).total_seconds()

            if duration >= LONG_RUNNING_THRESHOLD_SECONDS:
                alert = Alert(
                    id=str(uuid.uuid4()),
                    message=msg,
                    timestamp=now_utc,
                    room=room,
                    severity=Severity.CRITICAL,
                )
                added = db.add_alert(alert)
                if added:
                    logger.info("🚨 Alert: %s", msg)
                    if _discord_alert_callback:
                        await _discord_alert_callback(alert)
        else:
            _room_all_on_start[room] = None
            db.resolve_alerts_for_condition(room, "All devices have been ON")


