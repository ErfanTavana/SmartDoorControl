# SmartDoorControl

SmartDoorControl pairs a Django web backend with a MicroPython firmware for an ESP32-S3–driven door strike. The backend issues door-open commands, tracks access, and serves OTA payloads, while the device polls over HTTPS, toggles a single relay, and reports logs.

## Project structure
- `devices/firmware/main.py` — MicroPython firmware: Wi-Fi management, relay control, OTA checks, and backend polling.
- Django backend (root): `config/` settings and URLs plus feature apps:
  - `accounts/` custom `User` model with `HEAD` and `MEMBER` roles and login/logout views.
  - `households/` household/building/member management for heads of household.
  - `access/` member-facing door panel and access logs.
  - `devices/` device records, firmware payloads, command/ack endpoints, and log ingestion.
- Front-end styling: Tailwind-based CSS in `static/css/` with build scripts in `package.json`.

## Firmware behavior
The firmware in `devices/firmware/main.py` runs on boot and loops indefinitely:
1. **Hardware setup:** initializes GPIO16 as high-impedance (relay off) and drives it low to energize the relay when commanded.
2. **Connectivity:** scans configured Wi-Fi networks in priority order, reconnects as needed, and optionally starts WebREPL once connected.
3. **Watchdog & safety:** feeds a 30s hardware watchdog during waits; on unhandled errors it delays for 2 seconds before reset.
4. **Backend polling:** every 2 seconds it calls `GET /api/device/command/` with `X-DEVICE-TOKEN`; when `open` is true it pulses the relay for the requested duration and acknowledges via `POST /api/device/command/ack/`.
5. **Logging:** sends boot and heartbeat logs to `POST /api/device/logs/` with firmware/config versions and connection metadata.
6. **OTA:** every 60 seconds checks `GET /api/device/firmware/` for firmware/config content plus checksums; matching payloads are written to local files and the board is reset.

Key configuration constants (network list, server URL/token, GPIO pin, pulse duration, watchdog timeouts, OTA intervals, WebREPL toggle/password) live at the top of `devices/firmware/main.py` and must be edited before flashing.

## Backend capabilities
- **Roles & auth:** custom `User` model (`accounts.models.User`) adds `HEAD` and `MEMBER` roles. Heads land on the household dashboard; members on the door panel. Authentication uses Django’s built-in session login.
- **Households & members:** heads manage a single household/building; they can create member accounts with allowed time windows and activation flags via `households.views`.
- **Door access flow:**
  - Members submit door-open requests from `/door/`. Access is allowed when the member profile is active and within the configured time window; otherwise the attempt is logged as denied.
  - Heads can also trigger door commands for their household.
  - Commands are stored as `access.models.DoorCommand` records. Devices poll and mark commands executed via the ack endpoint; expired commands (older than 15 seconds) are marked accordingly during polling.
  - Each request writes an `AccessLog` entry indicating success or denial.
- **Device management:** each `devices.models.Device` belongs to a building and has a unique API token. Heads can view the last 200 device logs plus level/event breakdowns at `/devices/logs/`.
- **Firmware distribution & logs:** device firmware/config blobs are stored per-device (`DeviceFirmware`) with auto-generated SHA-256 checksums; devices fetch these payloads and push structured logs to `DeviceLog` records.

### Device API endpoints
All endpoints expect `X-DEVICE-TOKEN` to identify the device.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/device/command/` | Poll for the oldest pending door command; returns `{open: true, command_id, pulse_ms}` or `{open: false}`. Marks old commands (>15s) as expired. |
| `POST` | `/api/device/command/ack/` | Body: `{"command_id": <id>}`. Marks a command as executed. |
| `GET` | `/api/device/firmware/` | Returns firmware/config versions, content, and checksums for OTA. Empty object when no payload exists. |
| `POST` | `/api/device/logs/` | Body includes `message`, optional `level`, `event_type`, `firmware_version`, and `metadata`; stores a `DeviceLog` entry and updates `last_seen`. |

## Running the backend locally
Requirements: Python 3.11+ and SQLite (default). Tailwind build requires Node.js if you want to regenerate CSS.

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # optional, for admin access
python manage.py runserver
```

Static CSS is prebuilt at `static/css/tailwind.css`. To rebuild styles after editing `static/css/input.css`:
```bash
npm install
npm run build
```

## Flashing and configuring the firmware
1. Flash MicroPython to an ESP32-S3 board.
2. Update the constants near the top of `devices/firmware/main.py` with your Wi-Fi credentials, backend base URL, device token, and relay polarity/pin.
3. Upload `main.py` to the root of the device filesystem (WebREPL or serial transfer).
4. Power-cycle the board; it will connect to Wi-Fi, send a boot log, and begin polling the backend for commands and OTA updates.

## Limitations & notes
- Only a single relay GPIO is driven; no sensors/inputs are read by the firmware.
- Device endpoints rely solely on the API token for authentication; ensure tokens remain secret.
- Default Django settings enable `DEBUG` and SQLite; adjust for production deployments.

## License
This project is released under the MIT License. See [LICENSE](LICENSE).
