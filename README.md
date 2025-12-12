# SmartDoorControl IoT Firmware and Backend

## Project Overview
SmartDoorControl pairs a MicroPython-based ESP32-S3 door controller with a Django backend. The firmware drives a single relay to pulse a door strike and communicates with the server for commands, telemetry, and over-the-air (OTA) updates via HTTP.

## Hardware Components
- ESP32-S3 development board running MicroPython.
- Single relay channel connected to the ESP32 for door strike actuation (active-low control).

## Pin Configuration
| GPIO | Direction | Purpose | Notes |
| --- | --- | --- | --- |
| 16 | Output / High-Z | Relay control | Pulled low to energize relay; pin floats (input) to release. |

## Firmware Behavior
1. **Boot and setup**
   - Initializes the relay pin in a disabled (high-impedance) state.
   - Starts the hardware watchdog (30 s timeout) when available.
   - Connects to Wi-Fi using a prioritized list of configured networks.
   - Loads stored firmware and configuration version markers from local files.
2. **Main loop**
   - Ensures Wi-Fi connectivity; retries when disconnected.
   - Optionally starts WebREPL after Wi-Fi connects.
   - Sends a boot log once per restart with the current IP address.
   - Polls the backend every 2 seconds for open-door commands and fires the relay for the requested pulse duration (default 1000 ms) when `open` is true.
   - Acknowledges executed commands back to the server.
   - Checks for OTA firmware/config updates every 60 seconds and applies them when checksums match, then reboots.
   - Emits heartbeat logs every 60 seconds reporting firmware and config versions.
   - Feeds the watchdog during network waits and sleeps; on unhandled exceptions the board delays 2 seconds and resets.

## Communication & Protocols
- **Wi-Fi STA mode:** scans for configured SSIDs and connects in priority order; reconnection logic is built in.
- **HTTP (REST over TLS):**
  - `GET /api/device/command/` to poll for pending door commands.
  - `POST /api/device/command/ack/` to acknowledge executed commands.
  - `POST /api/device/logs/` to push structured device logs with metadata.
  - `GET /api/device/firmware/` to retrieve OTA firmware and configuration payloads.
- **WebREPL (optional):** starts when enabled and Wi-Fi is connected for interactive access over port 8266.

## Configuration Parameters
Key constants are defined in `devices/firmware/main.py`:
- Wi-Fi networks (`WIFI_NETWORKS` list with SSID, password, priority).
- Server base URL and device token (`SERVER_BASE_URL`, `DEVICE_TOKEN`).
- Relay settings (`RELAY_GPIO_PIN`, `RELAY_ACTIVE_LOW`, `RELAY_DEFAULT_PULSE_MS`).
- Polling and retry timings (`POLL_INTERVAL_MS`, `WATCHDOG_TIMEOUT_MS`, `REQUEST_TIMEOUT_SEC`, `RESET_DELAY_MS`).
- OTA controls (`OTA_ENABLED`, `OTA_ENDPOINT`, `OTA_CHECK_INTERVAL_MS`, version/checksum file names).
- Logging interval and WebREPL toggle/password.

## How to Flash / Upload the Firmware
1. Flash MicroPython to the ESP32-S3.
2. Update configuration constants in `devices/firmware/main.py` for your Wi-Fi credentials, server URL, device token, and relay polarity/pin as needed.
3. Upload `main.py` to the root of the device filesystem (e.g., via WebREPL or a serial file transfer tool) so it runs on boot.
4. Reboot the board; it will connect to Wi-Fi, start logging, and begin polling the backend.

## How to Use the Device
- Ensure the relay coil is wired to the controlled door hardware and its input line to GPIO16 (active-low).
- Provision the device token and firmware payload for the matching device record in the Django backend.
- Power up the ESP32-S3; once connected, it will poll the server and trigger the relay whenever the backend returns an `open` command.

## Limitations & Notes
- Only one relay output is controlled; no additional sensors or inputs are referenced in the firmware.
- WebREPL requires the configured password and an active Wi-Fi connection; it is skipped if the password is shorter than four characters.
- OTA updates rely on backend-provided content and checksums; mismatches prevent installation.
