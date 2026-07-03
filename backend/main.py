"""
Smart Office Monitor — FastAPI Application

Single source of truth: REST API, WebSocket real-time channel,
static file serving for the dashboard, and lifespan hooks that
start the simulator and (optionally) the Discord bot.
"""

import asyncio
import json
import logging
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend import database as db
from backend.config import ROOMS, DEVICE_SPECS, DISCORD_TOKEN
from backend.models import DeviceType
from backend.simulator import (
    run_simulator,
    set_broadcast_callback,
    set_alert_check_callback,
)
from backend.alerts import check_all_alerts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── WebSocket connection set ──────────────────────────────────────────────────
ws_connections: set[WebSocket] = set()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _room_summary(room: str) -> dict:
    """Build a JSON-serialisable summary dict for one room."""
    devs = db.get_devices_by_room(room)
    return {
        "name": room,
        "total_power": round(sum(d.power_draw for d in devs if d.status), 2),
        "fans_on":     len([d for d in devs if d.type == DeviceType.FAN and d.status]),
        "fans_total":  len([d for d in devs if d.type == DeviceType.FAN]),
        "lights_on":   len([d for d in devs if d.type == DeviceType.LIGHT and d.status]),
        "lights_total": len([d for d in devs if d.type == DeviceType.LIGHT]),
    }


def _full_state() -> dict:
    """Snapshot of the entire system for initial WS push or full refresh."""
    return {
        "type": "full_state",
        "data": {
            "devices":   [d.model_dump(mode="json") for d in db.get_all_devices()],
            "power":     db.get_power_summary(),
            "alerts":    [a.model_dump(mode="json") for a in db.get_active_alerts()],
            "rooms":     [_room_summary(r) for r in ROOMS],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


_ROOM_ALIASES: dict[str, str] = {
    "drawing":      "Drawing Room",
    "drawing_room": "Drawing Room",
    "drawing room": "Drawing Room",
    "work1":        "Work Room 1",
    "work_room_1":  "Work Room 1",
    "work room 1":  "Work Room 1",
    "work2":        "Work Room 2",
    "work_room_2":  "Work Room 2",
    "work room 2":  "Work Room 2",
}


def _resolve_room(name: str) -> str:
    """Normalise a user-supplied room name or raise 404."""
    normalised = _ROOM_ALIASES.get(name.lower().strip())
    if normalised:
        return normalised
    if name in ROOMS:
        return name
    raise HTTPException(
        status_code=404,
        detail=f"Room '{name}' not found.  Available: {', '.join(ROOMS)}",
    )


# ── WebSocket broadcast ──────────────────────────────────────────────────────

async def broadcast(event_type: str, device=None) -> None:
    """Push an update to every connected WebSocket client."""
    global ws_connections
    if not ws_connections:
        return

    if event_type == "full_state":
        message = _full_state()
    elif event_type == "device_update" and device:
        message = {
            "type": "device_update",
            "data": {
                "device":  device.model_dump(mode="json"),
                "power":   db.get_power_summary(),
                "alerts":  [a.model_dump(mode="json") for a in db.get_active_alerts()],
            },
        }
    else:
        message = _full_state()

    payload = json.dumps(message, default=str)
    dead: set[WebSocket] = set()

    for ws in ws_connections:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)

    ws_connections -= dead


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("🏢 Initialising Smart Office Monitor …")
    db.init_devices()
    logger.info("   %d devices across %d rooms", len(db.devices), len(ROOMS))

    set_broadcast_callback(broadcast)
    set_alert_check_callback(check_all_alerts)

    sim_task = asyncio.create_task(run_simulator())

    bot_task = None
    if DISCORD_TOKEN:
        try:
            from backend.bot import start_bot          # noqa: delay import
            bot_task = asyncio.create_task(start_bot())
            logger.info("   Discord bot started")
        except Exception:
            logger.exception("   Discord bot failed to start")
    else:
        logger.info("   DISCORD_TOKEN not set — bot disabled")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    sim_task.cancel()
    if bot_task:
        bot_task.cancel()
    logger.info("Smart Office Monitor shut down.")


# ── App creation ──────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Smart Office Monitor",
    description="Real-time monitoring system for office electrical devices",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def index():
    """Serve the dashboard SPA."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/devices")
async def api_devices():
    """All 15 devices with current state."""
    return db.get_all_devices()


@app.get("/api/rooms")
async def api_rooms():
    """Per-room summaries."""
    return [_room_summary(r) for r in ROOMS]


@app.get("/api/power")
async def api_power():
    """Office-wide power snapshot."""
    return db.get_power_summary()


@app.get("/api/alerts")
async def api_alerts():
    """All alerts (newest first)."""
    return [a.model_dump(mode="json") for a in db.get_all_alerts()]


@app.get("/api/room/{room_name}")
async def api_room(room_name: str):
    """Single room detail view with device list."""
    normalised = _resolve_room(room_name)
    devs = db.get_devices_by_room(normalised)
    return {
        "name":        normalised,
        "devices":     [d.model_dump(mode="json") for d in devs],
        "total_power": round(sum(d.power_draw for d in devs if d.status), 2),
        "fans_on":     len([d for d in devs if d.type == DeviceType.FAN and d.status]),
        "fans_total":  len([d for d in devs if d.type == DeviceType.FAN]),
        "lights_on":   len([d for d in devs if d.type == DeviceType.LIGHT and d.status]),
        "lights_total": len([d for d in devs if d.type == DeviceType.LIGHT]),
    }


@app.post("/api/devices/{device_id}/toggle")
async def api_toggle(device_id: str):
    """Manually toggle a device from the dashboard."""
    device = db.get_device(device_id)
    if not device:
        raise HTTPException(404, f"Device '{device_id}' not found")

    device.status = not device.status
    device.last_changed = datetime.now(timezone.utc)

    if device.status:
        base = DEVICE_SPECS[device.type.value]["base_power"]
        device.power_draw = round(base * random.uniform(0.85, 1.15), 2)
    else:
        device.power_draw = 0.0

    await check_all_alerts()
    await broadcast("device_update", device)
    return device.model_dump(mode="json")


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    ws_connections.add(ws)
    logger.info("WS ↑ connected  (total %d)", len(ws_connections))

    # Send initial full state
    try:
        await ws.send_text(json.dumps(_full_state(), default=str))
    except Exception:
        ws_connections.discard(ws)
        return

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("action") == "toggle" and msg.get("device_id"):
                    device = db.get_device(msg["device_id"])
                    if device:
                        device.status = not device.status
                        device.last_changed = datetime.now(timezone.utc)
                        if device.status:
                            base = DEVICE_SPECS[device.type.value]["base_power"]
                            device.power_draw = round(
                                base * random.uniform(0.85, 1.15), 2
                            )
                        else:
                            device.power_draw = 0.0
                        await check_all_alerts()
                        await broadcast("device_update", device)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        ws_connections.discard(ws)
        logger.info("WS ↓ disconnected  (total %d)", len(ws_connections))
