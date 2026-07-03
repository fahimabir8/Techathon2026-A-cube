"""
Smart Office Monitor — In-Memory Device Store

Holds the authoritative state for all 15 devices and alerts.
Every component (API, simulator, bot) reads/writes through these functions.
"""

from datetime import datetime, timezone

from backend.config import ROOMS, DEVICE_SPECS
from backend.models import Device, Alert, DeviceType


# ── In-memory stores ──────────────────────────────────────────────────────────
devices: dict[str, Device] = {}
alerts: list[Alert] = []


# ── Initialisation ────────────────────────────────────────────────────────────

def _room_key(room: str) -> str:
    """Convert a human room name to a short key for device IDs."""
    mapping = {
        "Drawing Room": "drawing",
        "Work Room 1":  "work1",
        "Work Room 2":  "work2",
    }
    return mapping.get(room, room.lower().replace(" ", "_"))


def init_devices() -> None:
    """Populate the store with the 15 office devices (all OFF)."""
    devices.clear()
    alerts.clear()

    for room in ROOMS:
        rk = _room_key(room)
        for device_type, spec in DEVICE_SPECS.items():
            for i in range(1, spec["count_per_room"] + 1):
                device_id = f"{device_type}_{rk}_{i}"
                devices[device_id] = Device(
                    id=device_id,
                    name=f"{device_type.capitalize()} {i}",
                    type=DeviceType(device_type),
                    room=room,
                    status=False,
                    power_draw=0.0,
                    last_changed=datetime.now(timezone.utc),
                )


# ── Device queries ────────────────────────────────────────────────────────────

def get_all_devices() -> list[Device]:
    return list(devices.values())


def get_device(device_id: str) -> Device | None:
    return devices.get(device_id)


def get_devices_by_room(room: str) -> list[Device]:
    return [d for d in devices.values() if d.room == room]


# ── Power helpers ─────────────────────────────────────────────────────────────

def get_power_summary() -> dict:
    total = 0.0
    room_powers: dict[str, float] = {}

    for room in ROOMS:
        room_power = sum(
            d.power_draw for d in get_devices_by_room(room) if d.status
        )
        room_powers[room] = round(room_power, 2)
        total += room_power

    # Simple daily estimate: watts → kWh over 24 h
    estimated_daily = round(total * 24 / 1000, 2)

    return {
        "total_power": round(total, 2),
        "rooms": room_powers,
        "estimated_daily_kwh": estimated_daily,
    }


# ── Alert management ─────────────────────────────────────────────────────────

def add_alert(alert: Alert) -> bool:
    """Add an alert if an identical active one does not already exist."""
    for existing in alerts:
        if (
            not existing.resolved
            and existing.room == alert.room
            and existing.message == alert.message
        ):
            return False
    alerts.append(alert)
    return True


def get_active_alerts() -> list[Alert]:
    return [a for a in alerts if not a.resolved]


def get_all_alerts() -> list[Alert]:
    return sorted(alerts, key=lambda a: a.timestamp, reverse=True)


def resolve_alerts_for_condition(room: str, keyword: str) -> None:
    """Resolve all active alerts for *room* whose message contains *keyword*."""
    for alert in alerts:
        if not alert.resolved and alert.room == room and keyword in alert.message:
            alert.resolved = True
