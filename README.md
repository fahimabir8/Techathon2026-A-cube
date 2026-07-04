# 🏢 Smart Office Monitoring System

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

#install uv (if you don't have)
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


# discord
## command usage
you can use straight up prefix commnds.
1. `!status` - show all room status
2. `!room <room>` - show details on a specific room
3. `!usage` - show current power consumption

this commands are taken from rulebook. 
## ai
you can use natural english instead of commands. for example:
<img width="507" height="162" alt="image" src="https://github.com/user-attachments/assets/c1c159e2-0779-4108-8e34-704201b470fe" />

## deployment
i used ollama in my old laptop without gpu. i had to run two distinct model for getting accurate data output. you can use one single model with better system prompt. for a one day hackathon, i dont have that much energy. 

modelfile are included in `/discord` directory. and better documentation given in `/discord/readme`.

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

![Hardware Schematic](hardware%20schematic/schematic.png)

## Device Mapping

| Device | Device ID | LED Pin | Button Pin |
|---------|-----------|---------|------------|
| Fan 1 | `fan_work1_1` | GPIO 21 | GPIO 34 |
| Fan 2 | `fan_work1_2` | GPIO 5 | GPIO 35 |
| Light 1 | `light_work1_1` | GPIO 17 | GPIO 25 |
| Light 2 | `light_work1_2` | GPIO 2 | GPIO 27 |
| Light 3 | `light_work1_3` | GPIO 15 | GPIO 13 |

---

## 📁 Project Structure

```
Techathon2026-A-cube/
├── backend/
│   ├── __init__.py        # Package marker
│   ├── config.py          # Environment & constants
├── discord/
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
