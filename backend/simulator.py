"""
Smart Office Monitor — Device Simulator

Background async loop that randomly toggles device states every few seconds
to simulate a live office environment.
"""

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from backend.config import (
    DEVICE_SPECS,
    SIMULATION_MIN_INTERVAL,
    SIMULATION_MAX_INTERVAL,
    OFFICE_HOURS_START,
    OFFICE_HOURS_END,
)
from backend import database as db

logger = logging.getLogger(__name__)

# Callbacks wired by main.py at startup
_broadcast_callback: Callable[..., Coroutine[Any, Any, None]] | None = None
_alert_check_callback: Callable[..., Coroutine[Any, Any, None]] | None = None


def set_broadcast_callback(callback: Callable) -> None:
    global _broadcast_callback
    _broadcast_callback = callback


def set_alert_check_callback(callback: Callable) -> None:
    global _alert_check_callback
    _alert_check_callback = callback


async def run_simulator() -> None:
    """Main simulation loop — runs forever as an asyncio background task."""
    logger.info("🔄 Device simulator started")

    # Determine initial office hours status
    now_local = db.get_current_time()
    was_office_hours = (OFFICE_HOURS_START <= now_local.hour < OFFICE_HOURS_END)

    # ── Warm-up: randomly turn ON ~7 devices so the dashboard is interesting (only if in office hours) ──
    if was_office_hours:
        all_devices = list(db.devices.values())
        for device in random.sample(all_devices, k=min(7, len(all_devices))):
            device.status = True
            base = DEVICE_SPECS[device.type.value]["base_power"]
            device.power_draw = round(base * random.uniform(0.85, 1.15), 2)
            device.last_changed = db.get_current_utc_time()

    # Push initial full state to any already-connected WS client
    if _broadcast_callback:
        await _broadcast_callback("full_state")

    # ── Main loop ─────────────────────────────────────────────────────────────
    while True:
        # Check office hours at each tick before determining simulation interval
        now_local = db.get_current_time()
        is_office_hours = (OFFICE_HOURS_START <= now_local.hour < OFFICE_HOURS_END)

        if not is_office_hours:
            if was_office_hours:
                # Transition: Office hours just ended. Stop automatic simulator toggles.
                logger.info("🕒 Office hours ended. Stopping automatic simulator toggles.")
                if _alert_check_callback:
                    await _alert_check_callback()
                if _broadcast_callback:
                    await _broadcast_callback("full_state")
                was_office_hours = False

            # Outside office hours: sleep 1 second and check again.
            await asyncio.sleep(1)
            continue

        # If office hours:
        if not was_office_hours:
            # Transition: Office hours just started.
            logger.info("🕒 Office hours started. Resuming automatic simulator toggles.")
            was_office_hours = True

        # Normal simulation tick
        interval = random.uniform(SIMULATION_MIN_INTERVAL, SIMULATION_MAX_INTERVAL)
        await asyncio.sleep(interval)

        try:
            # Recheck office hours after sleep
            now_local = db.get_current_time()
            if not (OFFICE_HOURS_START <= now_local.hour < OFFICE_HOURS_END):
                continue

            device = random.choice(list(db.devices.values()))
            device.status = not device.status
            device.last_changed = db.get_current_utc_time()

            if device.status:
                base = DEVICE_SPECS[device.type.value]["base_power"]
                device.power_draw = round(base * random.uniform(0.85, 1.15), 2)
            else:
                device.power_draw = 0.0

            logger.debug(
                "Toggled %s → %s (%sW)",
                device.id,
                "ON" if device.status else "OFF",
                device.power_draw,
            )

            # Evaluate alert rules after each state change
            if _alert_check_callback:
                await _alert_check_callback()

            # Push update to all WebSocket clients
            if _broadcast_callback:
                await _broadcast_callback("device_update", device)

        except Exception:
            logger.exception("Simulator tick error")
