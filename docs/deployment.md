# 🚀 Smart Office Monitor — Deployment Guide

This document describes how to deploy the Smart Office Monitor project to production or staging environments, focusing on the Vercel platform.

---

## ☁️ Vercel Deployment

Vercel hosts the backend as serverless functions and serves the static files (HTML, CSS, JavaScript) from the Vercel Edge Network.

### 1. Project Layout Configuration
The deployment is controlled by [vercel.json](file:///home/abir/coding/Techathon2026-A-cube/vercel.json):
* **Backend:** `/backend/main.py` is configured as the serverless function build target using `@vercel/python`.
* **Frontend:** `/static/**` files are configured as static build targets.
* **Routing:** API endpoints (`/api/*` and `/ws`) route directly to the backend function. All other routes fall back to the SPA frontend (`static/index.html`).

### 2. Dependency Resolution
The Python serverless function builder on Vercel installs libraries listed in the root [requirements.txt](file:///home/abir/coding/Techathon2026-A-cube/requirements.txt) during deployment. Ensure this file is updated if any dependencies are added to `pyproject.toml`.

### 3. Vercel Dashboard Settings
1. Go to your **Vercel Dashboard** and click **Add New** > **Project**.
2. Import the GitHub Repository.
3. Configure the following settings:
   * **Framework Preset:** `Other` (Vercel automatically detects `vercel.json` and configures builds).
   * **Root Directory:** `./`
4. Expand **Environment Variables** and add the following keys if you want to enable the Discord Integration:
   * `DISCORD_TOKEN`: Your Discord application bot token.
   * `DISCORD_CHANNEL_ID`: Channel ID for posting alert notifications.
5. Click **Deploy**.

---

## ⚠️ Important Production Limitations

Because Vercel executes the backend in a serverless environment, the following design changes/limitations apply:

### 1. In-Memory Database Reset
The current implementation (`backend/database.py`) uses Python `dict` and `list` variables for storage. 
* **Vercel Serverless Functions** are ephemeral and spin down when idle. When they spin down, the database state resets back to default (all devices off, all alerts cleared).
* Multiple concurrent users might hit different serverless instances, leading to split states.
* **Solution:** For production usage, swap the `backend/database.py` store to read and write to a persistent database such as **PostgreSQL** or **Redis**.

### 2. Background Tasks & Discord Bot
* **FastAPI Lifespan Tasks** (`run_simulator()` and `start_bot()`) will not run continuously on Vercel because Vercel kills serverless processes after requests complete (maximum duration is 10–60 seconds).
* **Discord Bot:** Running `discord.py` inside a Vercel serverless function is not supported as Vercel functions cannot hold open websocket connections to Discord.
* **Solution:** Host the Discord bot and/or the background simulator on a dedicated persistent server (such as Render, Railway, Fly.io, or an EC2 instance), while hosting the API/Dashboard on Vercel. Alternatively, configure **Vercel Cron Jobs** to trigger state changes periodically.
