<p align="right">
  <a href="./README.fa.md">🇮🇷 فارسی</a>
</p>

# SmartDoorControl

SmartDoorControl pairs a Django web backend with MicroPython firmware running on an ESP32-S3 to drive a single relay for door release. The ESP32 polls the backend over HTTP, triggers the relay when a command is queued, and reports status and logs back to the server. The backend provides household management, web/PWA access to trigger door opens, and device-facing endpoints for commands, firmware, and logging.

## System Architecture
- **Device (ESP32-S3 + relay):** connects to Wi-Fi, polls the backend every few seconds, activates the relay when instructed, and periodically uploads logs and firmware/config version data. A watchdog guards the main loop and the board resets after fatal errors.【F:devices/firmware/main.py†L1-L130】【F:devices/firmware/main.py†L718-L829】
- **Backend (Django):** stores buildings/households, user accounts with head/member roles, door commands, access logs, device firmware payloads, and device logs. Session-authenticated users interact through HTML views; devices authenticate with an API token in `X-DEVICE-TOKEN`.【F:config/settings.py†L1-L74】【F:devices/models.py†L9-L64】【F:access/models.py†L1-L44】【F:devices/urls.py†L1-L11】

## Hardware Components
- ESP32-S3 running MicroPython.
- Single relay channel driven directly from an ESP32 GPIO.
- Wi-Fi network connectivity.

### Default Wiring & Pinout
| Signal | Default GPIO | Notes |
| --- | --- | --- |
| Relay control | 16 | Active-low by default; the firmware drives the pin low to energize and reconfigures it to input (high-Z) to release. Configurable via constants.【F:devices/firmware/main.py†L41-L67】【F:devices/firmware/main.py†L82-L105】

## Firmware Behavior
1. **Configuration:** Constants at the top of `devices/firmware/main.py` define Wi-Fi SSIDs/passwords with priority, backend base URL, API token, relay polarity/pin, pulse duration, watchdog and poll intervals, OTA endpoints, and WebREPL settings. Edit these before flashing.【F:devices/firmware/main.py†L17-L70】
2. **Boot & connectivity:** The relay is set to a safe off state, Wi-Fi is activated, and the board scans configured networks in priority order. It retries connections, optionally resets the interface on failures, and can start WebREPL once connected.【F:devices/firmware/main.py†L82-L279】【F:devices/firmware/main.py†L653-L699】
3. **Watchdog:** A hardware watchdog with a 30s timeout is fed throughout network waits and the main loop; unhandled exceptions trigger a short delay then board reset.【F:devices/firmware/main.py†L27-L70】【F:devices/firmware/main.py†L624-L716】【F:devices/firmware/main.py†L829-L843】
4. **Polling cycle:** Every `POLL_INTERVAL_MS` (default 2s) the device ensures Wi-Fi is connected, sends a boot log once, polls for a command, triggers the relay when `open` is true, acknowledges executed commands, optionally performs OTA checks, logs a heartbeat every minute, and then sleeps for the poll interval.【F:devices/firmware/main.py†L718-L829】
5. **Relay control:** The relay is activated for the requested pulse duration (milliseconds) using active-low logic, then released to high impedance.【F:devices/firmware/main.py†L678-L695】
6. **Logging:** Logs include boot, command execution, and periodic heartbeat messages with firmware/config versions and Wi-Fi metadata; they are posted to the backend log endpoint and mirrored to stdout.【F:devices/firmware/main.py†L513-L574】【F:devices/firmware/main.py†L718-L807】
7. **OTA updates:** When enabled, the device checks `/api/device/firmware/` (default every 60s) for firmware and config payloads with checksums. New payloads are written to local files and a reset is requested so updates apply on boot.【F:devices/firmware/main.py†L576-L652】
8. **Error handling:** Network and API exceptions are caught to keep the loop alive; fatal errors fall through to a reset, and the watchdog forces a reset if the loop stalls.【F:devices/firmware/main.py†L439-L523】【F:devices/firmware/main.py†L829-L843】

## Device ↔ Backend API
All device endpoints expect `X-DEVICE-TOKEN` for authentication.【F:devices/views.py†L25-L41】【F:devices/urls.py†L1-L11】

| Method | Path | Request body | Response | Notes |
| --- | --- | --- | --- | --- |
| `GET` | `/api/device/command/` | — | `{open: true, command_id, pulse_ms}` or `{open: false}` | Expired commands (>15s) are marked before returning the oldest pending command.【F:devices/views.py†L43-L78】 |
| `POST` | `/api/device/command/ack/` | `{"command_id": <id>}` | `{status: "ok"}` or error | Marks a command executed with timestamp; returns 404 if not pending.【F:devices/views.py†L81-L110】 |
| `GET` | `/api/device/firmware/` | — | `{version, content, checksum, config, config_version, config_checksum}` or `{}` | Supplies firmware/config blobs and checksums for OTA.【F:devices/views.py†L112-L134】 |
| `POST` | `/api/device/logs/` | `{message, level?, event_type?, firmware_version?, metadata?}` | `{status: "ok"}` or error | Stores a `DeviceLog`, updates `last_seen`, and enriches metadata with IP and user-agent.【F:devices/views.py†L136-L171】 |

## Backend Responsibilities
- **User roles:** Custom `accounts.User` adds `HEAD` and `MEMBER` roles. Heads manage households/buildings; members are linked to a household profile with allowed time windows and activation flag.【F:accounts/models.py†L1-L19】【F:households/models.py†L1-L35】
- **Households & buildings:** Each household belongs to a building, and each building can have devices that inherit the building’s commands/logs scope.【F:households/models.py†L1-L23】【F:devices/models.py†L9-L30】
- **Access flow:**
  - Heads land on a dashboard; members use the door panel at `/door/` to request access.【F:access/views.py†L1-L46】
  - Access is granted when the member profile is active and within the configured time range; otherwise a denied `AccessLog` entry is written. Successful requests create a `DoorCommand` and a success log; heads can trigger commands without schedule checks.【F:access/views.py†L22-L65】【F:access/models.py†L1-L44】
  - Commands belong to the device for the household’s building. Devices poll/ack commands; expired commands are marked by the polling view.【F:access/models.py†L1-L19】【F:devices/views.py†L43-L78】
- **Device admin views:** Household heads can review the 200 most recent device logs plus level and event breakdowns at `/devices/logs/`.【F:devices/views.py†L173-L198】
- **Firmware storage:** Each device can have an associated `DeviceFirmware` record storing firmware and config blobs; checksums are computed on save for OTA verification.【F:devices/models.py†L31-L64】

## Web / PWA Interface
- Base templates register a web manifest and service worker to support installable/standalone use.【F:templates/base/base.html†L1-L13】
- The service worker precaches the home and `/door/` routes plus manifest and icons, updates cache versions on activation, and falls back to cache on fetch failures.【F:static/service-worker.js†L1-L36】
- Manifest metadata defines names, colors, icons, and start URL rooted at `/`.【F:static/manifest.json†L1-L21】

## Configuration Parameters (firmware)
- **Network & server:** `WIFI_NETWORKS` list with priorities, `SERVER_BASE_URL`, `DEVICE_TOKEN`, and HTTP endpoints for command, ack, log, and OTA checks.【F:devices/firmware/main.py†L17-L55】
- **Relay:** `RELAY_GPIO_PIN`, `RELAY_ACTIVE_LOW`, `RELAY_DEFAULT_PULSE_MS`.【F:devices/firmware/main.py†L37-L45】
- **Timing:** `POLL_INTERVAL_MS`, `OTA_CHECK_INTERVAL_MS`, `VERSION_LOG_INTERVAL_MS`, `WATCHDOG_TIMEOUT_MS`, `REQUEST_TIMEOUT_SEC`, `RESET_DELAY_MS`.【F:devices/firmware/main.py†L41-L70】
- **OTA files:** Paths for firmware/config versions and checksums persisted on the device (`firmware_version.txt`, `firmware_checksum.txt`, `device_config.json`, etc.).【F:devices/firmware/main.py†L55-L66】
- **Diagnostics:** `WEBREPL_ENABLED` and `WEBREPL_PASSWORD` toggle the built-in WebREPL server.【F:devices/firmware/main.py†L67-L70】

## Flashing & Deploying the Device
1. Flash MicroPython to an ESP32-S3 board.
2. Edit the configuration constants at the top of `devices/firmware/main.py` to set Wi-Fi credentials, backend URL, device token, GPIO pin/polarity, and timing/OTA preferences.【F:devices/firmware/main.py†L17-L70】
3. Upload `main.py` to the device filesystem (e.g., WebREPL or serial transfer).
4. Reboot the board. On boot it initializes the relay, connects to Wi-Fi, sends a boot log, and enters the polling loop for commands and OTA updates.【F:devices/firmware/main.py†L82-L279】【F:devices/firmware/main.py†L718-L807】

## Running the Backend Locally
Requirements: Python 3.11+ with SQLite (default). Tailwind CSS rebuilds require Node.js if you edit `static/css/input.css`.

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # optional for admin access
python manage.py runserver
```

Static CSS is prebuilt at `static/css/tailwind.css`. Rebuild after changes with:

```bash
npm install
npm run build
```

## Limitations & Notes
- Firmware drives only one relay and reads no inputs/sensors.【F:devices/firmware/main.py†L37-L45】【F:devices/firmware/main.py†L678-L695】
- Device authentication relies solely on the API token; no TLS configuration or certificate pinning is present in the firmware code.【F:devices/views.py†L25-L41】【F:devices/firmware/main.py†L439-L523】
- Django settings default to `DEBUG=True`, SQLite, and open `ALLOWED_HOSTS`; adjust for production deployments.【F:config/settings.py†L16-L47】

## Future Work
- The repository mentions potential NFC, PIN, or fingerprint-based access but these are not implemented in the current codebase.
