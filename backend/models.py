"""
Smart Office Monitor — Data Models

Pydantic models shared by the backend API, simulator, alert engine, and Discord bot.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class DeviceType(str, Enum):
    """Physical device category."""
    FAN = "fan"
    LIGHT = "light"


class Severity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ── Core Domain Models ────────────────────────────────────────────────────────

class Device(BaseModel):
    """A single monitored electrical device."""
    id: str
    name: str
    type: DeviceType
    room: str
    status: bool = False
    power_draw: float = 0.0
    last_changed: datetime


class Alert(BaseModel):
    """A system-generated alert."""
    id: str
    message: str
    timestamp: datetime
    room: str
    severity: Severity = Severity.WARNING
    resolved: bool = False
    resolved_at: datetime | None = None


# ── API Response Models ───────────────────────────────────────────────────────

class RoomSummary(BaseModel):
    """Aggregated view of a single room."""
    name: str
    devices: list[Device]
    total_power: float
    fans_on: int
    fans_total: int
    lights_on: int
    lights_total: int


class PowerSummary(BaseModel):
    """Office-wide power consumption snapshot."""
    total_power: float
    rooms: dict[str, float]
    estimated_daily_kwh: float
