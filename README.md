# 🏢 Smart Office Monitor

> **Techathon 2026 — Team A-Cube**
>
> Real-time monitoring system for a simulated smart office with 15 electrical devices across 3 rooms.

![Python](https://img.shields.io/badge/Python-3.13+-3776ab?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Discord.py](https://img.shields.io/badge/Discord.py-2.3+-5865f2?style=flat-square&logo=discord&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## ✨ Features

| Component | Description |
|-----------|-------------|
| **Real-Time Dashboard** | Glassmorphic dark-mode UI with live WebSocket updates, animated fan/light icons, floor-plan visualization, and toast alerts |
| **Device Simulator** | Background async task that randomly toggles 15 devices every 3–8 seconds |
| **Alert Engine** | Auto-generates warnings for after-hours usage and long-running rooms |
| **Discord Bot** | `!status`, `!room <name>`, `!usage` commands with rich embeds + auto-posted alerts |
| **REST API** | Full CRUD-style endpoints for devices, rooms, power, and alerts |
| **WebSocket** | Push-based real-time channel at `/ws` — no polling |

---

## 🏗️ Architecture

```
              ┌──────────────────┐
              │  Device Simulator│
              │  (async task)    │
              └────────┬─────────┘
                       │ updates
                       ▼
           ┌───────────────────────┐
           │   FastAPI Backend     │
           │  ┌─────────────────┐  │
           │  │ In-Memory Store │  │
           │  └─────────────────┘  │
           │  ┌─────────────────┐  │
           │  │  Alert Engine   │  │
           │  └─────────────────┘  │
           │  ┌─────────────────┐  │
           │  │  REST + WS API  │  │
           │  └─────────────────┘  │
           └───┬──────────┬────────┘
               │          │
        ┌──────▼──┐  ┌────▼──────┐
        │Dashboard│  │Discord Bot│
        │ (HTML)  │  │(discord.py)│
        └─────────┘  └───────────┘
```

---

## 🏠 Office Layout

| Room | Fans | Lights | Devices |
|------|------|--------|---------|
| Drawing Room | 2 | 3 | 5 |
| Work Room 1 | 2 | 3 | 5 |
| Work Room 2 | 2 | 3 | 5 |
| **Total** | **6** | **9** | **15** |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** package manager (recommended)

### 1. Clone & install

```bash
git clone https://github.com/your-team/Techathon2026-A-cube.git
cd Techathon2026-A-cube

# Install dependencies with uv
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in DISCORD_TOKEN if you want bot functionality
```

### 3. Run

```bash
# Using uv
uv run python main.py

# Or directly
python main.py

# Or with uvicorn
uvicorn backend.main:app --reload
```

Open **http://localhost:8000** to view the dashboard.

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/devices` | All 15 devices with current state |
| `GET` | `/api/rooms` | Room-level summaries |
| `GET` | `/api/power` | Total & room-wise power draw |
| `GET` | `/api/alerts` | All alerts (newest first) |
| `GET` | `/api/room/{name}` | Single room detail (accepts `drawing`, `work1`, `work2`) |
| `POST` | `/api/devices/{id}/toggle` | Toggle a device ON/OFF |
| `WS` | `/ws` | Real-time update channel |

---

## 🤖 Discord Bot Commands

| Command | Description |
|---------|-------------|
| `!status` | Office-wide device summary |
| `!room <name>` | Detail for one room (`drawing`, `work1`, `work2`) |
| `!usage` | Current power & estimated daily kWh |

Set `DISCORD_TOKEN` and `DISCORD_CHANNEL_ID` in `.env` for auto-posted alert notifications.

---

## 🔔 Alert Rules

1. **After-Hours Usage** — Any device ON outside 9 AM–5 PM triggers a warning.
2. **Long-Running Room** — All devices in one room ON for > 2 hours triggers a critical alert.

Both thresholds are configurable via environment variables (see `.env.example`).

---

## 🔌 Hardware Schematic (Conceptual)

For a real deployment, one representative room would use:

```
  ┌─────────────┐       ┌─────────────┐
  │   ESP32      │ GPIO  │  4-Channel  │
  │  DevKit V1   ├──────►│  Relay      │
  │              │       │  Module     │
  └──────┬───────┘       └──┬──┬──┬───┘
         │                  │  │  │
    ┌────┴────┐      ┌─────┘  │  └──────┐
    │ ACS712  │      │        │         │
    │ Current │    Fan 1    Fan 2    Light 1-3
    │ Sensor  │   (AC)     (AC)     (AC)
    └─────────┘
```

### Pin Mapping (ESP32)

| GPIO | Connected To | Purpose |
|------|-------------|---------|
| 23 | Relay IN1 | Fan 1 control |
| 22 | Relay IN2 | Fan 2 control |
| 21 | Relay IN3 | Light 1 control |
| 19 | Relay IN4 | Light 2 control |
| 18 | Relay IN5* | Light 3 control |
| 34 | ACS712 OUT | Current sensing (ADC) |
| VIN | Relay VCC | 5V power to relay module |
| GND | Common GND | Shared ground |

*\*Uses a second relay module or a 5th channel.*

**Electrical Notes:**
- Relays switch AC mains (220V) — use optocoupler-isolated relay modules for safety.
- ACS712 (5A variant) provides analog output proportional to current draw.
- ESP32 ADC reads 0–3.3V on GPIO34; apply voltage divider if sensor outputs > 3.3V.
- Firmware would POST readings to the backend REST API over WiFi.

---

## 📁 Project Structure

```
Techathon2026-A-cube/
├── backend/
│   ├── __init__.py        # Package marker
│   ├── config.py          # Environment & constants
│   ├── models.py          # Pydantic data models
│   ├── database.py        # In-memory device/alert store
│   ├── simulator.py       # Background device toggling
│   ├── alerts.py          # Alert evaluation engine
│   ├── bot.py             # Discord bot commands
│   └── main.py            # FastAPI app + WebSocket + lifespan
├── static/
│   ├── index.html         # Dashboard SPA
│   ├── styles.css         # Glassmorphic design system
│   └── app.js             # WebSocket client + DOM rendering
├── main.py                # Convenience entry point
├── pyproject.toml         # Dependencies
├── .env.example           # Environment template
└── README.md              # This file
```

---

## 👥 Team A-Cube

| Name | Email | Phone |
|------|-------|-------|
| Nafisa Rahman | nafisa.rahman@yahoo.com | +8801812345678 |
| Tanvir Hossain | tanvir.hossain@yahoo.com | +8801912345678 |

---

## 📄 License

MIT © 2026 Team A-Cube
