/* ═══════════════════════════════════════════════════════════════════════════
   Smart Office Monitor — Dashboard Logic
   WebSocket-first with REST fallback, dynamic DOM updates, toast alerts
   ═══════════════════════════════════════════════════════════════════════════ */

(() => {
  "use strict";

  // ── State ──────────────────────────────────────────────────────────────────
  let devices  = [];   // current device list
  let alerts   = [];   // active alerts
  let power    = {};   // { total_power, rooms, estimated_daily_kwh }
  let rooms    = [];   // room summaries
  let ws       = null;
  let reconnectTimer = null;
  const RECONNECT_DELAY = 3000;
  const OFFICE_START = 9;
  const OFFICE_END   = 17;

  // Determine the backend base URL and WebSocket URL
  // If served from VS Code Live Server (typically ports 5500/5501), connect to port 8001 or 8080.
  // A query parameter "?port=8001" or "?backend_port=8001" can also override the default port.
  function getBackendUrls() {
    const urlParams = new URLSearchParams(window.location.search);
    const queryPort = urlParams.get("port") || urlParams.get("backend_port");
    const isLiveServer = location.port === "5500" || location.port === "5501";
    
    // Default to port 8001 (as fastapi dev is running on 8001) or 8080 (the default main.py port)
    const backendPort = queryPort || (isLiveServer ? "8001" : (location.port || "8080"));
    const wsProto = location.protocol === "https:" ? "wss" : "ws";
    
    let httpBase, wsBase;
    if (isLiveServer || queryPort) {
      httpBase = `${location.protocol}//${location.hostname}:${backendPort}`;
      wsBase = `${wsProto}://${location.hostname}:${backendPort}`;
    } else {
      httpBase = "";
      wsBase = `${wsProto}://${location.host}`;
    }
    return { httpBase, wsBase };
  }

  const { httpBase, wsBase } = getBackendUrls();

  // ── DOM refs ───────────────────────────────────────────────────────────────
  const $totalPower   = document.getElementById("total-power-value");
  const $dailyKwh     = document.getElementById("daily-kwh-value");
  const $devicesOn    = document.getElementById("devices-on-value");
  const $alertsCount  = document.getElementById("alerts-count-value");
  const $alertBadge   = document.getElementById("alert-badge-count");
  const $alertsList   = document.getElementById("alerts-list");
  const $roomsGrid    = document.getElementById("rooms-grid");
  const $connBadge    = document.getElementById("connection-badge");
  const $connText     = document.getElementById("connection-text");
  const $officeHours  = document.getElementById("office-hours-badge");
  const $officeText   = document.getElementById("office-hours-text");
  const $clock        = document.getElementById("clock");
  const $toasts       = document.getElementById("toast-container");



  // ── Room visual config ─────────────────────────────────────────────────────
  const ROOM_META = {
    "Drawing Room": { emoji: "🛋️", cssClass: "room-drawing" },
    "Work Room 1":  { emoji: "💻", cssClass: "room-work1" },
    "Work Room 2":  { emoji: "📐", cssClass: "room-work2" },
  };

  const DEVICE_EMOJI = { fan: "🌀", light: "💡" };


  // ═════════════════════════════════════════════════════════════════════════
  // Clock & Office Hours
  // ═════════════════════════════════════════════════════════════════════════

  function tickClock() {
    const now = new Date();
    $clock.textContent = now.toLocaleTimeString("en-US", { hour12: true });

    const h = now.getHours();
    const inOffice = h >= OFFICE_START && h < OFFICE_END;

    $officeText.textContent = inOffice ? "Office Hours" : "After Hours";
    $officeHours.className  = `badge ${inOffice ? "badge-success" : "badge-danger"}`;
  }
  setInterval(tickClock, 1000);
  tickClock();


  // ═════════════════════════════════════════════════════════════════════════
  // WebSocket
  // ═════════════════════════════════════════════════════════════════════════

  function connectWS() {
    ws = new WebSocket(`${wsBase}/ws`);

    ws.onopen = () => {
      setConnStatus("connected");
      clearTimeout(reconnectTimer);
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        handleMessage(msg);
      } catch { /* ignore malformed frames */ }
    };

    ws.onclose = () => {
      setConnStatus("disconnected");
      scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  function scheduleReconnect() {
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connectWS, RECONNECT_DELAY);
  }

  function setConnStatus(state) {
    if (state === "connected") {
      $connBadge.className = "badge badge-success";
      $connText.textContent = "Live";
    } else {
      $connBadge.className = "badge badge-warning";
      $connText.textContent = "Reconnecting…";
    }
  }


  // ═════════════════════════════════════════════════════════════════════════
  // Message handler
  // ═════════════════════════════════════════════════════════════════════════

  function handleMessage(msg) {
    if (msg.type === "full_state") {
      devices = msg.data.devices || [];
      power   = msg.data.power   || {};
      alerts  = msg.data.alerts  || [];
      rooms   = msg.data.rooms   || [];
      renderAll();
    } else if (msg.type === "device_update") {
      // Patch single device
      const updated = msg.data.device;
      if (updated) {
        const idx = devices.findIndex(d => d.id === updated.id);
        if (idx !== -1) devices[idx] = updated; else devices.push(updated);
      }
      power  = msg.data.power  || power;

      // Check for new alerts
      const newAlerts = msg.data.alerts || [];
      const oldIds = new Set(alerts.map(a => a.id));
      for (const a of newAlerts) {
        if (!oldIds.has(a.id)) {
          showToast(a.message, a.severity);
        }
      }
      alerts = newAlerts;

      renderMetrics();
      renderAlerts();
      // Re-render only the affected room card
      if (updated) {
        renderRoomCard(updated.room);
      }
    }
  }


  // ═════════════════════════════════════════════════════════════════════════
  // Render functions
  // ═════════════════════════════════════════════════════════════════════════

  function renderAll() {
    renderMetrics();
    renderRooms();
    renderAlerts();
  }

  // ── Metrics ────────────────────────────────────────────────────────────────
  function renderMetrics() {
    const total = power.total_power ?? 0;
    $totalPower.textContent = `${total.toFixed(1)} W`;
    $dailyKwh.textContent   = `${(power.estimated_daily_kwh ?? 0).toFixed(2)} kWh`;

    const onCount = devices.filter(d => d.status).length;
    $devicesOn.textContent  = `${onCount} / ${devices.length}`;

    $alertsCount.textContent = alerts.length;
    $alertBadge.textContent  = alerts.length;

    // Highlight total-power card colour based on load
    const metricCard = document.getElementById("metric-total-power");
    metricCard.classList.toggle("high-load", total > 300);
  }

  // ── Rooms grid ─────────────────────────────────────────────────────────────
  function renderRooms() {
    const roomNames = [...new Set(devices.map(d => d.room))];
    // Sort: Drawing Room first
    roomNames.sort((a, b) => {
      const order = { "Drawing Room": 0, "Work Room 1": 1, "Work Room 2": 2 };
      return (order[a] ?? 99) - (order[b] ?? 99);
    });

    $roomsGrid.innerHTML = "";
    for (const room of roomNames) {
      $roomsGrid.appendChild(buildRoomCard(room));
    }
  }

  function renderRoomCard(roomName) {
    const existing = $roomsGrid.querySelector(`[data-room="${roomName}"]`);
    const newCard = buildRoomCard(roomName);
    if (existing) {
      existing.replaceWith(newCard);
    } else {
      $roomsGrid.appendChild(newCard);
    }
  }

  function buildRoomCard(roomName) {
    const meta = ROOM_META[roomName] || { emoji: "🏠", cssClass: "" };
    const roomDevices = devices.filter(d => d.room === roomName);
    const roomPower = (power.rooms && power.rooms[roomName]) ?? 0;

    const card = document.createElement("div");
    card.className = `room-card ${meta.cssClass}`;
    card.setAttribute("data-room", roomName);

    // Header
    const header = document.createElement("div");
    header.className = "room-card-header";
    header.innerHTML = `
      <h3><span class="room-icon">${meta.emoji}</span> ${roomName}</h3>
      <span class="room-power-badge">⚡ ${roomPower.toFixed(1)} W</span>
    `;
    card.appendChild(header);

    // Devices
    const grid = document.createElement("div");
    grid.className = "room-devices";

    // Sort: fans first, then lights
    const sorted = [...roomDevices].sort((a, b) => {
      if (a.type === b.type) return a.name.localeCompare(b.name);
      return a.type === "fan" ? -1 : 1;
    });

    for (const dev of sorted) {
      grid.appendChild(buildDeviceTile(dev));
    }

    card.appendChild(grid);
    return card;
  }

  function buildDeviceTile(dev) {
    const tile = document.createElement("div");
    tile.className = `device-tile${dev.status ? " device-on" : " device-off"}`;
    tile.id = `tile-${dev.id}`;

    const iconClass = dev.type === "fan" ? "icon-fan" : "icon-light";
    const statusText = dev.status
      ? `ON · ${dev.power_draw.toFixed(1)}W`
      : "OFF";

    // SVG propeller for fans, emoji for lights
    let iconContent;
    if (dev.type === "fan") {
      iconContent = `<svg class="fan-propeller" viewBox="0 0 64 64" fill="currentColor" width="22" height="22">
        <circle cx="32" cy="32" r="5"/>
        <ellipse cx="32" cy="14" rx="6" ry="14" />
        <ellipse cx="50" cy="32" rx="14" ry="6" />
        <ellipse cx="32" cy="50" rx="6" ry="14" />
        <ellipse cx="14" cy="32" rx="14" ry="6" />
      </svg>`;
    } else {
      iconContent = DEVICE_EMOJI[dev.type] || "⚙️";
    }

    // Apply grey style to light icon when device is OFF
    const offClass = (!dev.status && dev.type === "light") ? " icon-off" : "";

    tile.innerHTML = `
      <div class="device-tile-icon ${iconClass}${offClass}">${iconContent}</div>
      <div class="device-tile-info">
        <div class="device-tile-name">${dev.name}</div>
        <div class="device-tile-status">${statusText}</div>
      </div>
    `;

    tile.addEventListener("click", () => toggleDevice(dev.id));
    return tile;
  }

  // ── Alerts ─────────────────────────────────────────────────────────────────
  function renderAlerts() {
    if (alerts.length === 0) {
      $alertsList.innerHTML = '<div class="alert-empty">No active alerts ✓</div>';
      return;
    }

    $alertsList.innerHTML = "";
    // newest first
    const sorted = [...alerts].sort(
      (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
    );

    for (const alert of sorted) {
      const item = document.createElement("div");
      item.className = `alert-item severity-${alert.severity || "warning"}`;

      const time = new Date(alert.timestamp).toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      });
      const severityEmoji = { warning: "⚠️", critical: "🚨", info: "ℹ️" };

      item.innerHTML = `
        <div class="alert-message">${severityEmoji[alert.severity] || "⚠️"} ${alert.message}</div>
        <div class="alert-meta">
          <span>📍 ${alert.room}</span>
          <span>🕐 ${time}</span>
        </div>
      `;
      $alertsList.appendChild(item);
    }
  }




  // ═════════════════════════════════════════════════════════════════════════
  // Device toggle (sends WS message or REST fallback)
  // ═════════════════════════════════════════════════════════════════════════

  function toggleDevice(deviceId) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: "toggle", device_id: deviceId }));
    } else {
      // REST fallback
      fetch(`${httpBase}/api/devices/${deviceId}/toggle`, { method: "POST" })
        .then(r => r.json())
        .then(() => fetchFullState())
        .catch(console.error);
    }
  }

  // REST fallback for initial load when WS isn't ready
  async function fetchFullState() {
    try {
      const [devRes, pwrRes, alertRes] = await Promise.all([
        fetch(`${httpBase}/api/devices`),
        fetch(`${httpBase}/api/power`),
        fetch(`${httpBase}/api/alerts`),
      ]);
      devices = await devRes.json();
      power   = await pwrRes.json();
      alerts  = (await alertRes.json()).filter(a => !a.resolved);
      renderAll();
    } catch (e) {
      console.error("REST fallback error:", e);
    }
  }


  // ═════════════════════════════════════════════════════════════════════════
  // Toast notifications
  // ═════════════════════════════════════════════════════════════════════════

  function showToast(message, severity = "warning") {
    const emojiMap = { warning: "⚠️", critical: "🚨", info: "ℹ️" };
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = `
      <span class="toast-icon">${emojiMap[severity] || "⚠️"}</span>
      <span>${message}</span>
    `;
    $toasts.appendChild(toast);

    setTimeout(() => {
      toast.classList.add("toast-exit");
      toast.addEventListener("animationend", () => toast.remove());
    }, 5000);
  }


  // ═════════════════════════════════════════════════════════════════════════
  // Initialise
  // ═════════════════════════════════════════════════════════════════════════

  connectWS();
  // Also do a one-time REST fetch so we have data even before WS connects
  fetchFullState();

})();
