# 📡 Smart Office Monitor — API Documentation

This document describes all available REST and WebSocket endpoints of the Smart Office Monitor backend, including the recently added timestamp-based query system.

---

## 🔒 Authentication & Headers
All API responses return JSON and accept standard CORS requests (`allow_origins=["*"]`). Currently, no authentication tokens are required for these endpoints.

---

## ⚡ REST Endpoints

### 1. Retrieve Devices
Get current status, configuration, and power draw for all 15 simulated devices.
* **Method:** `GET`
* **Path:** `/api/devices`
* **Response Example:**
  ```json
  [
    {
      "id": "fan_drawing_1",
      "name": "Fan 1",
      "type": "fan",
      "room": "Drawing Room",
      "status": true,
      "power_draw": 72.5,
      "last_changed": "2026-07-04T12:00:00Z"
    }
  ]
  ```

### 2. Retrieve Room Summary
Get aggregated metrics for each room.
* **Method:** `GET`
* **Path:** `/api/rooms`
* **Response Example:**
  ```json
  [
    {
      "name": "Drawing Room",
      "total_power": 150.2,
      "fans_on": 1,
      "fans_total": 2,
      "lights_on": 2,
      "lights_total": 3
    }
  ]
  ```

### 3. Retrieve Room Details
Get full detail of a single room, including its devices and summarized load.
* **Method:** `GET`
* **Path:** `/api/room/{room_name}`
* **Path Parameters:**
  * `room_name` (string): The room name or alias (e.g. `drawing`, `work1`, `work2`).
* **Response Example:**
  ```json
  {
    "name": "Work Room 1",
    "devices": [...],
    "total_power": 65.8,
    "fans_on": 1,
    "fans_total": 2,
    "lights_on": 1,
    "lights_total": 3
  }
  ```

### 4. Retrieve Power Summary
Get total office power usage and estimated daily kWh.
* **Method:** `GET`
* **Path:** `/api/power`
* **Response Example:**
  ```json
  {
    "total_power": 216.0,
    "rooms": {
      "Drawing Room": 150.2,
      "Work Room 1": 65.8,
      "Work Room 2": 0.0
    },
    "estimated_daily_kwh": 5.18
  }
  ```

### 5. Retrieve Alerts (with Timestamp Filtering)
Retrieve a list of system alerts. Supports time-based queries to inspect alert status at specific moments or over an interval.
* **Method:** `GET`
* **Path:** `/api/alerts`
* **Query Parameters:**
  * `time` (string, ISO-8601 format, optional): Returns alerts active at this exact moment. An alert was active at `T` if it was created at or before `T` and either unresolved or resolved after `T`.
  * `start` (string, ISO-8601 format, optional): Start of range query. Returns alerts active at any point from `start` onwards.
  * `end` (string, ISO-8601 format, optional): End of range query. Omit to default to the current time.
* **Response Example (Flat Array):**
  ```json
  [
    {
      "id": "a90dfb21-4f36-47b2-8419-450f3b4da672",
      "message": "Light 2 in Work Room 1 is ON after office hours",
      "timestamp": "2026-07-04T18:00:00Z",
      "resolved_at": "2026-07-04T19:00:00Z",
      "room": "Work Room 1",
      "severity": "warning",
      "resolved": true
    }
  ]
  ```

### 6. Toggle Device Status
Manually toggle the state (ON/OFF) of a device.
* **Method:** `POST`
* **Path:** `/api/devices/{device_id}/toggle`
* **Path Parameters:**
  * `device_id` (string): ID of the device (e.g. `light_drawing_2`).
* **Response Example:**
  ```json
  {
    "id": "light_drawing_2",
    "name": "Light 2",
    "type": "light",
    "room": "Drawing Room",
    "status": true,
    "power_draw": 14.2,
    "last_changed": "2026-07-04T15:10:00Z"
  }
  ```

### 7. Set Manual Time Override
Manually override the local simulator time (for testing office hour alert rules) or reset to current system time.
* **Method:** `POST`
* **Path:** `/api/set-time`
* **Query Parameters:**
  * `time` (string, format `HH:MM`, optional): Omit to reset back to local system time.
* **Response Example:**
  ```json
  {
    "status": "ok",
    "current_time": "2026-07-04T19:30:00.123456"
  }
  ```

---

## 🔌 WebSocket Endpoint

* **URL:** `/ws`
* **Protocol:** `ws://` / `wss://`
* **Description:** Establishes a persistent real-time JSON channel. Updates are pushed to clients instantly whenever device states change or alerts are generated.

### Server to Client Events

#### 1. Full State Update
Pushed immediately upon connection.
```json
{
  "type": "full_state",
  "data": {
    "devices": [...],
    "power": {...},
    "alerts": [...],
    "rooms": [...],
    "timestamp": "2026-07-04T15:47:00Z"
  }
}
```

#### 2. Device Update
Pushed when a device is toggled.
```json
{
  "type": "device_update",
  "data": {
    "device": {
      "id": "fan_drawing_1",
      "status": false,
      ...
    },
    "power": {...},
    "alerts": [...]
  }
}
```

### Client to Server Messages

#### Toggle Device State
Clients can send messages to toggle devices without sending REST POST requests:
```json
{
  "action": "toggle",
  "device_id": "light_work1_1"
}
```
