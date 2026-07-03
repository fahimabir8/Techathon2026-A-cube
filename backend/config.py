"""
Smart Office Monitor — Configuration

Central configuration for rooms, devices, simulation, alerts, and Discord.
All environment-variable overrides are loaded from a .env file at project root.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Office Layout ─────────────────────────────────────────────────────────────
ROOMS: list[str] = ["Drawing Room", "Work Room 1", "Work Room 2"]

DEVICE_SPECS: dict[str, dict] = {
    "fan":   {"base_power": 60, "count_per_room": 2},
    "light": {"base_power": 15, "count_per_room": 3},
}

# ── Simulation ────────────────────────────────────────────────────────────────
SIMULATION_MIN_INTERVAL: float = float(os.getenv("SIM_MIN_INTERVAL", "3"))
SIMULATION_MAX_INTERVAL: float = float(os.getenv("SIM_MAX_INTERVAL", "8"))

# ── Office Hours ──────────────────────────────────────────────────────────────
OFFICE_HOURS_START: int = int(os.getenv("OFFICE_HOURS_START", "9"))   # 9 AM
OFFICE_HOURS_END:   int = int(os.getenv("OFFICE_HOURS_END", "17"))    # 5 PM

# ── Alert Thresholds ──────────────────────────────────────────────────────────
LONG_RUNNING_THRESHOLD_SECONDS: int = int(
    os.getenv("ALERT_LONG_RUNNING_THRESHOLD_SECONDS", "7200")
)

# ── Discord ───────────────────────────────────────────────────────────────────
DISCORD_TOKEN:          str = os.getenv("DISCORD_TOKEN", "")
DISCORD_CHANNEL_ID:     str = os.getenv("DISCORD_CHANNEL_ID", "")
DISCORD_COMMAND_PREFIX: str = os.getenv("DISCORD_COMMAND_PREFIX", "!")
