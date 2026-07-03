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

  // Chart and Floor Plan layouts
  let chart = null;
  const powerHistory = [];
  const maxHistoryLength = 25;
  const chartSampleMs = 2000;
  const timeDisplayOptions = {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  };

  const DEVICE_LAYOUT = {
    // Drawing Room
    "fan_drawing_1":   { type: "fan",   left: "50%", top: "20%" },
    "fan_drawing_2":   { type: "fan",   left: "50%", top: "72%" },
    "light_drawing_1": { type: "light", left: "22%", top: "15%" },
    "light_drawing_2": { type: "light", left: "78%", top: "15%" },
    "light_drawing_3": { type: "light", left: "50%", top: "86%" },

    // Work Room 1
    "fan_work1_1":   { type: "fan",   left: "50%", top: "20%" },
    "fan_work1_2":   { type: "fan",   left: "50%", top: "72%" },
    "light_work1_1": { type: "light", left: "22%", top: "15%" },
    "light_work1_2": { type: "light", left: "78%", top: "15%" },
    "light_work1_3": { type: "light", left: "50%", top: "86%" },

    // Work Room 2
    "fan_work2_1":   { type: "fan",   left: "50%", top: "20%" },
    "fan_work2_2":   { type: "fan",   left: "50%", top: "72%" },
    "light_work2_1": { type: "light", left: "22%", top: "15%" },
    "light_work2_2": { type: "light", left: "78%", top: "15%" },
    "light_work2_3": { type: "light", left: "50%", top: "86%" },
  };

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
  // Chart.js - Power Usage Graph
  // ═════════════════════════════════════════════════════════════════════════

  function getDashboardTime() {
    return manualTime ? new Date(manualTime.getTime()) : new Date();
  }

  function formatDashboardTime(date) {
    return date.toLocaleTimeString("en-US", timeDisplayOptions);
  }

  function syncChartTimeLabels() {
    if (!chart) return;
    const endTime = getDashboardTime().getTime();
    powerHistory.forEach((point, index) => {
      const stepsFromEnd = powerHistory.length - 1 - index;
      point.time = new Date(endTime - stepsFromEnd * chartSampleMs);
    });
    chart.data.labels = powerHistory.map(d => formatDashboardTime(d.time));
    chart.update("none");
  }

  function initChart() {
    const $canvas = document.getElementById("power-chart");
    if (!$canvas) return;
    const ctx = $canvas.getContext("2d");
    
    const currentPower = power.total_power ?? 0;
    const now = getDashboardTime().getTime();
    for (let i = 0; i < maxHistoryLength; i++) {
      powerHistory.push({ time: new Date(now - (maxHistoryLength - i) * chartSampleMs), value: currentPower });
    }

    chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: powerHistory.map(d => formatDashboardTime(d.time)),
        datasets: [{
          label: "Total Power",
          data: powerHistory.map(d => d.value),
          borderColor: "#6366f1",
          backgroundColor: (context) => {
            const chartArea = context.chart.chartArea;
            if (!chartArea) return null;
            const chartCtx = context.chart.ctx;
            const gradient = chartCtx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
            gradient.addColorStop(0, "rgba(99, 102, 241, 0.35)");
            gradient.addColorStop(1, "rgba(99, 102, 241, 0.0)");
            return gradient;
          },
          fill: true,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          pointHoverBackgroundColor: "#6366f1",
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            mode: "index",
            intersect: false,
            backgroundColor: "rgba(15, 23, 42, 0.95)",
            titleColor: "#94a3b8",
            bodyColor: "#f1f5f9",
            borderColor: "rgba(148, 163, 184, 0.12)",
            borderWidth: 1,
            padding: 8,
            displayColors: false,
            callbacks: {
              label: function(context) {
                return `Total Power: ${context.parsed.y.toFixed(1)} W`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: "#64748b",
              font: { size: 9 },
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 5
            }
          },
          y: {
            grid: { color: "rgba(148, 163, 184, 0.05)" },
            ticks: {
              color: "#64748b",
              font: { size: 9 },
              callback: function(val) { return `${val} W`; }
            },
            min: 0,
            suggestedMax: 300
          }
        }
      }
    });
  }

  function updateChartRolling() {
    if (!chart) return;
    const currentPower = power.total_power ?? 0;
    powerHistory.push({ time: getDashboardTime(), value: currentPower });
    if (powerHistory.length > maxHistoryLength) {
      powerHistory.shift();
    }
    chart.data.labels = powerHistory.map(d => formatDashboardTime(d.time));
    chart.data.datasets[0].data = powerHistory.map(d => d.value);
    chart.update("none");
  }

  // ═════════════════════════════════════════════════════════════════════════
  // CSS Floor Plan layout
  // ═════════════════════════════════════════════════════════════════════════

  const $officeLayout = document.getElementById("office-layout");

  function renderBaseLayout() {
    if (!$officeLayout) return;
    $officeLayout.innerHTML = "";

    const roomConfigs = [
      { name: "Drawing Room", class: "layout-room-drawing", alias: "drawing" },
      { name: "Work Room 1",  class: "layout-room-work1",   alias: "work1" },
      { name: "Work Room 2",  class: "layout-room-work2",   alias: "work2" },
    ];

    roomConfigs.forEach(room => {
      const roomDiv = document.createElement("div");
      roomDiv.className = `layout-room ${room.class}`;
      roomDiv.innerHTML = `
        <div class="room-label">${room.name}</div>
      `;

      if (room.alias === "drawing") {
        // Sofa
        const sofa = document.createElement("div");
        sofa.className = "furniture sofa-drawing";
        roomDiv.appendChild(sofa);

        // Coffee Table
        const table = document.createElement("div");
        table.className = "furniture coffee-table-drawing";
        roomDiv.appendChild(table);

        // Armchair
        const armchair = document.createElement("div");
        armchair.className = "furniture armchair-drawing";
        roomDiv.appendChild(armchair);

        // Plants
        const plant1 = document.createElement("div");
        plant1.className = "plant-icon";
        plant1.style.left = "5%";
        plant1.style.top = "5%";
        plant1.textContent = "🌿";
        roomDiv.appendChild(plant1);

        const plant2 = document.createElement("div");
        plant2.className = "plant-icon";
        plant2.style.right = "5%";
        plant2.style.bottom = "5%";
        plant2.textContent = "🌿";
        roomDiv.appendChild(plant2);

        // Door
        const door = document.createElement("div");
        door.className = "layout-door door-drawing";
        roomDiv.appendChild(door);
      }

      if (room.alias === "work1" || room.alias === "work2") {
        const desks = [
          { left: "8%", top: "25%", w: "24%", h: "16%" },
          { left: "68%", top: "25%", w: "24%", h: "16%" },
          { left: "8%", top: "58%", w: "24%", h: "16%" },
          { left: "68%", top: "58%", w: "24%", h: "16%" },
        ];

        desks.forEach(desk => {
          const deskDiv = document.createElement("div");
          deskDiv.className = "furniture desk-layout";
          deskDiv.style.left = desk.left;
          deskDiv.style.top = desk.top;
          deskDiv.style.width = desk.w;
          deskDiv.style.height = desk.h;
          
          const pc = document.createElement("div");
          pc.className = "pc-monitor";
          deskDiv.appendChild(pc);

          roomDiv.appendChild(deskDiv);
        });

        // Door
        const door = document.createElement("div");
        door.className = `layout-door door-${room.alias}`;
        roomDiv.appendChild(door);
      }

      $officeLayout.appendChild(roomDiv);
    });

    const hallwayDiv = document.createElement("div");
    hallwayDiv.className = "layout-hallway";
    hallwayDiv.innerHTML = `
      <div class="plant-icon" style="left: 2%; top: 25%;">🌿</div>
      <div class="layout-door door-main"></div>
      <div class="entrance-arrow">↑</div>
      <div class="plant-icon" style="right: 18%; top: 25%;">🌿</div>
      <div class="dispenser-layout">
        <div class="dispenser-bottle"></div>
      </div>
    `;
    $officeLayout.appendChild(hallwayDiv);
  }

  function renderDevicesOnLayout() {
    if (!$officeLayout) return;

    const roomsList = ["Drawing Room", "Work Room 1", "Work Room 2"];
    roomsList.forEach(roomName => {
      const roomKey = roomName === "Drawing Room" ? "drawing" : (roomName === "Work Room 1" ? "work1" : "work2");
      const roomDiv = $officeLayout.querySelector(`.layout-room-${roomKey}`);
      if (!roomDiv) return;

      const existingDevices = roomDiv.querySelectorAll(".layout-device");
      existingDevices.forEach(d => d.remove());

      const roomDevices = devices.filter(d => d.room === roomName);
      roomDevices.forEach(dev => {
        const layoutMeta = DEVICE_LAYOUT[dev.id];
        if (!layoutMeta) return;

        const devDiv = document.createElement("div");
        devDiv.className = `layout-device device-${layoutMeta.type} ${dev.status ? 'device-on' : 'device-off'}`;
        devDiv.style.left = layoutMeta.left;
        devDiv.style.top = layoutMeta.top;
        devDiv.setAttribute("data-device-id", dev.id);
        
        const stateText = dev.status ? `ON (${dev.power_draw.toFixed(0)}W)` : 'OFF';
        devDiv.setAttribute("data-tooltip", `${dev.name} is ${stateText}`);
        const leftValue = parseFloat(layoutMeta.left);
        const topValue = parseFloat(layoutMeta.top);
        if (leftValue < 30) {
          devDiv.setAttribute("data-tooltip-x", "left");
        } else if (leftValue > 70) {
          devDiv.setAttribute("data-tooltip-x", "right");
        }
        if (topValue < 25) {
          devDiv.setAttribute("data-tooltip-y", "below");
        }

        if (layoutMeta.type === "fan") {
          devDiv.innerHTML = `<svg class="fan-propeller" viewBox="0 0 64 64" fill="currentColor" width="12" height="12">
            <circle cx="32" cy="32" r="5"/>
            <ellipse cx="32" cy="14" rx="6" ry="14" />
            <ellipse cx="50" cy="32" rx="14" ry="6" />
            <ellipse cx="32" cy="50" rx="6" ry="14" />
            <ellipse cx="14" cy="32" rx="14" ry="6" />
          </svg>`;
        } else {
          devDiv.innerHTML = `<svg viewBox="0 0 24 24" fill="none" width="8" height="8" stroke="currentColor" stroke-width="2.5">
            <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .5 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5" stroke-linecap="round"/>
            <path d="M9 18h6M10 22h4" stroke-linecap="round"/>
          </svg>`;
        }

        devDiv.addEventListener("click", (e) => {
          e.stopPropagation();
          toggleDevice(dev.id);
        });

        roomDiv.appendChild(devDiv);
      });
    });
  }

  // ═════════════════════════════════════════════════════════════════════════
  // Clock & Office Hours
  // ═════════════════════════════════════════════════════════════════════════

  let manualTime = null; // Will store a Date object if user overrides

  function tickClock() {
    let now;
    if (manualTime) {
      // Increment manualTime by 1 second
      manualTime = new Date(manualTime.getTime() + 1000);
      now = manualTime;
      $clock.classList.add("simulated");
      $clock.title = "Manual Time active. Click to edit, double-click to reset.";
    } else {
      now = new Date();
      $clock.classList.remove("simulated");
      $clock.title = "Click to set manual time";
    }

    // Only update text content if we're not currently editing
    if (!$clock.querySelector('.clock-input')) {
      $clock.textContent = formatDashboardTime(now);
    }

    const h = now.getHours();
    const inOffice = h >= OFFICE_START && h < OFFICE_END;

    $officeText.textContent = inOffice ? "Office Hours" : "After Hours";
    $officeHours.className  = `badge ${inOffice ? "badge-success" : "badge-danger"}`;
  }

  // Handle single click to edit
  $clock.addEventListener("click", () => {
    if ($clock.querySelector('.clock-input')) return;

    const now = manualTime || new Date();
    const hrs = String(now.getHours()).padStart(2, '0');
    const mins = String(now.getMinutes()).padStart(2, '0');

    const input = document.createElement("input");
    input.type = "time";
    input.className = "clock-input";
    input.value = `${hrs}:${mins}`;

    // Inline styling to fit badge perfectly
    input.style.background = "transparent";
    input.style.border = "none";
    input.style.color = "var(--text-primary)";
    input.style.fontFamily = "inherit";
    input.style.fontSize = "inherit";
    input.style.fontWeight = "inherit";
    input.style.outline = "none";
    input.style.width = "75px";
    input.style.textAlign = "center";
    input.style.cursor = "text";

    $clock.innerHTML = "";
    $clock.appendChild(input);
    input.focus();

    // Prevent propagation
    input.addEventListener("click", (e) => e.stopPropagation());

    const syncTimeWithBackend = (timeStr) => {
      const url = timeStr ? `${httpBase}/api/set-time?time=${timeStr}` : `${httpBase}/api/set-time`;
      fetch(url, { method: "POST" })
        .then(r => r.json())
        .catch(console.error);
    };

    const saveTime = () => {
      const val = input.value;
      if (val === "") {
        manualTime = null;
        syncTimeWithBackend(null);
      } else {
        const [hours, minutes] = val.split(":").map(Number);
        const temp = new Date();
        temp.setHours(hours);
        temp.setMinutes(minutes);
        temp.setSeconds(0);
        manualTime = temp;
        syncTimeWithBackend(val);
      }
      $clock.innerHTML = "";
      tickClock();
      syncChartTimeLabels();
    };

    input.addEventListener("blur", saveTime);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        saveTime();
      } else if (e.key === "Escape") {
        $clock.innerHTML = "";
        tickClock();
      }
    });
  });

  // Handle double click to reset
  $clock.addEventListener("dblclick", () => {
    manualTime = null;
    const url = `${httpBase}/api/set-time`;
    fetch(url, { method: "POST" })
      .then(r => r.json())
      .catch(console.error);
    tickClock();
    syncChartTimeLabels();
  });

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
      // Re-render only the affected room card and layout
      if (updated) {
        renderRoomCard(updated.room);
        renderDevicesOnLayout();
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
    renderDevicesOnLayout();
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

    // Update real-time chart immediately for instant feedback
    if (chart && powerHistory.length > 0) {
      powerHistory[powerHistory.length - 1].value = total;
      chart.data.datasets[0].data = powerHistory.map(d => d.value);
      chart.update("none");
    }
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

  renderBaseLayout();
  initChart();
  setInterval(updateChartRolling, 2000);

  connectWS();
  // Also do a one-time REST fetch so we have data even before WS connects
  fetchFullState();

})();
