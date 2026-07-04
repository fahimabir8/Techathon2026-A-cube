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

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** package manager (recommended)

### 1. Clone & install

```bash
git clone https://github.com/your-team/Techathon2026-A-cube.git
cd Techathon2026-A-cube

#install uv 
pip install uv

# Install dependencies with uv
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env

#.env example 
TOKEN="rtenmraengmen"
BACKEND_API="http://127.0.0.1:8080/api"

AI_API=http://localhost:11434/v1/chat/completions
AI_MODEL_INTENT=discord-intent
AI_MODEL_RESPOND=discord-respond
ALERT_CHANNEL_ID="1391205043457491044"
AI_CHANNEL_ID="1391205043457491044"
```

### 3. Run

```bash
# Using uv
uv run main.py
# Or with uvicorn
uvicorn backend.main:app --reload
```

Open **http://localhost:8000** to view the dashboard.

---

## 📡 API Reference

Detailed API specifications, payload schemas, and WebSocket instructions are available in the [API Documentation](docs/api.md).

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/devices` | All 15 devices with current state |
| `GET` | `/api/rooms` | Room-level summaries |
| `GET` | `/api/power` | Total & room-wise power draw |
| `GET` | `/api/alerts` | Get alerts. Supports filtering: `time` (exact active alert at time), `start`, and `end` range. |
| `GET` | `/api/room/{name}` | Single room detail (accepts `drawing`, `work1`, `work2`) |
| `POST` | `/api/devices/{id}/toggle` | Toggle a device ON/OFF |
| `WS` | `/ws` | Real-time update channel |

---

## ☁️ Deployment

For deploying the project to cloud platforms (such as **Vercel**), please refer to the [Deployment Guide](docs/deployment.md).

---

## 🤖 Discord Bot Commands

| Command | Description |
|---------|-------------|
| `!status` | Office-wide device summary |
| `!room <name>` | Detail for one room (`drawing`, `work1`, `work2`) |
| `!usage` | Current power & estimated daily kWh |

Set `DISCORD_TOKEN` and `DISCORD_CHANNEL_ID` in `.env` for auto-posted alert notifications.

Also we have implemented AI to humanize bot's responses. A separate channel can be used to talk directly and get AI generated response from user.

---

## 🔔 Alert Rules

1. **After-Hours Usage** — Any device ON outside 9 AM–5 PM triggers a warning.
2. **Long-Running Room** — All devices in one room ON for > 2 hours triggers a critical alert.

Both thresholds are configurable via environment variables (see `.env.example`).

---
# ESP32 Room Simulation

This project simulates one office room consisting of **2 fans** and **3 lights** using an ESP32.

Each device is represented by:

- Push Button → User toggles the device
- LED → Represents the current ON/OFF state

The ESP32 communicates with the FastAPI backend over Wi-Fi. Whenever a button is pressed, it sends a request to the backend. The backend updates the device state, broadcasts the change to the dashboard via WebSockets, checks for alerts, and the ESP32 synchronizes its LEDs by periodically fetching the latest device states.

---

# Architecture

```
              Button Press
                    │
                    ▼
                 ESP32
                    │
      POST /api/devices/{id}/toggle
                    │
                    ▼
            FastAPI Backend
                    │
        ┌───────────┼────────────┐
        │           │            │
        ▼           ▼            ▼
     Database   Web Dashboard  Discord Bot
                    ▲
                    │
        GET /api/devices (1 second)
                    │
                    ▼
                 ESP32 LEDs
```

---

# Device Mapping

| Device | Device ID | LED Pin | Button Pin |
|---------|-----------|---------|------------|
| Fan 1 | `fan_work1_1` | GPIO 21 | GPIO 34 |
| Fan 2 | `fan_work1_2` | GPIO 5 | GPIO 35 |
| Light 1 | `light_work1_1` | GPIO 17 | GPIO 25 |
| Light 2 | `light_work1_2` | GPIO 2 | GPIO 27 |
| Light 3 | `light_work1_3` | GPIO 15 | GPIO 13 |

---

# ESP32 Pin Diagram

```
                ESP32 DEVKIT V1

           +-----------------------+

GPIO21 -------------------- LED 1 (Fan 1)

GPIO5  -------------------- LED 2 (Fan 2)

GPIO17 -------------------- LED 3 (Light 1)

GPIO2  -------------------- LED 4 (Light 2)

GPIO15 -------------------- LED 5 (Light 3)



GPIO34 <------------------- Push Button 1

GPIO35 <------------------- Push Button 2

GPIO25 <------------------- Push Button 3

GPIO27 <------------------- Push Button 4

GPIO13 <------------------- Push Button 5

           +-----------------------+
```

---

# Button Wiring

Each button is connected as:

```
3.3V
 │
 │
Button
 │
GPIOxx
 │
10kΩ
 │
GND
```

Alternatively, use the ESP32's internal pull-up resistor by configuring:

```cpp
pinMode(pin, INPUT_PULLUP);
```

Then wire the button between the GPIO pin and GND.

---

# LED Wiring

Each LED should be connected with a current-limiting resistor.

```
GPIOxx
 │
220Ω
 │
LED (+)
LED (-)
 │
GND
```

---

# API Communication

### Toggle Device

```
POST /api/devices/{device_id}/toggle
```

Example

```
POST /api/devices/fan_work1_1/toggle
```

---

### Synchronize Device States

```
GET /api/devices
```

Example Response

```json
[
    {
        "id": "fan_work1_1",
        "status": true
    },
    {
        "id": "fan_work1_2",
        "status": false
    },
    {
        "id": "light_work1_1",
        "status": true
    }
]
```

The ESP32 polls this endpoint every second to keep the LEDs synchronized with the backend.

---

# Room Devices

```
Work Room 1

├── Fan 1
├── Fan 2
├── Light 1
├── Light 2
└── Light 3
```

---

# Hardware Components

- ESP32 DevKit V1
- 5 × LEDs
- 5 × 220Ω Resistors
- 5 × Push Buttons
- 5 × 10kΩ Resistors (if not using INPUT_PULLUP)
- Breadboard
- Jumper Wires
- USB Cable

---

# Notes

- The backend is the **single source of truth**.
- LEDs never determine the actual device state.
- Button presses only send toggle requests.
- The dashboard, Discord bot, and ESP32 always stay synchronized through the backend.
- This hardware setup represents **one room**. The remaining rooms are simulated by the backend using the same device model.

---

## 📁 Project Structure

```
Techathon2026-A-cube/
├── backend/
│   ├── __init__.py        # Package marker
│   ├── config.py          # Environment & constants
|   discord/
|    ├── .env.example
|    ├── .gitignore
|    ├── ai.py
|    ├── alert.py
|    ├── bot.py
|    ├── cmd.py
|    ├── Modelfile.intent
|    ├── Modelfile.respond
|    ├── README.md
|    └── docs/
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

| Name |
|------|
| Abdullah Al Muaz|
| Asfaqur Rahman Khan |
| Md. Fahim Hossain Abir |

---

## 📄 License

MIT © 2026 Team A-Cube
