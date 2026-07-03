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

    # ── Warm-up: randomly turn ON ~7 devices so the dashboard is interesting ──
    all_devices = list(db.devices.values())
    for device in random.sample(all_devices, k=min(7, len(all_devices))):
        device.status = True
        base = DEVICE_SPECS[device.type.value]["base_power"]
        device.power_draw = round(base * random.uniform(0.85, 1.15), 2)
        device.last_changed = datetime.now(timezone.utc)

    # Push initial full state to any already-connected WS client
    if _broadcast_callback:
        await _broadcast_callback("full_state")

    # ── Main loop ─────────────────────────────────────────────────────────────
    while True:
        interval = random.uniform(SIMULATION_MIN_INTERVAL, SIMULATION_MAX_INTERVAL)
        await asyncio.sleep(interval)

        try:
            device = random.choice(list(db.devices.values()))
            device.status = not device.status
            device.last_changed = datetime.now(timezone.utc)

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
