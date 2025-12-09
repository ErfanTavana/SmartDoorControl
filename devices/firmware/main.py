"""
MicroPython firmware for ESP32-S3 door controller.

Features:
- WiFi connection with reconnection handling.
- Polling a Django backend for open-door commands.
- Relay control with configurable active polarity.
- Safe error handling for network and API issues.
"""

import errno
import json
import os
import time
import network
import machine

try:
    import urequests as requests
except ImportError:  # Fallback for environments that alias urequests
    import requests

# ========================
# Configuration
# ========================
SSID = "1283"
PASSWORD = "0928007634"
SERVER_BASE_URL = "https://erfantavanasmartdoor.pythonanywhere.com/"  # No trailing slash
DEVICE_TOKEN = "nm5bbP3TA4qHpi2DrBqkcaDgmcFEIvwScv1IedyklPA"
RELAY_GPIO_PIN = 5
RELAY_ACTIVE_LOW = True  # Set to True if the relay is active-low
POLL_INTERVAL_MS = 5000
COMMAND_ENDPOINT = "/api/device/command/"
ACK_ENDPOINT = "/api/device/command/ack/"
OTA_ENABLED = True
OTA_ENDPOINT = "/api/device/firmware/"
OTA_CHECK_INTERVAL_MS = 300000  # 5 minutes
FIRMWARE_VERSION = "1.0.0"
FIRMWARE_VERSION_FILE = "firmware_version.txt"
WATCHDOG_TIMEOUT_MS = 15000
RESET_DELAY_MS = 2000
# HTTP request timeout (in seconds). Increase to allow slower responses before failing.
REQUEST_TIMEOUT_SEC = 15

# ========================
# Hardware setup
# ========================
relay_pin = machine.Pin(RELAY_GPIO_PIN, machine.Pin.OUT)


def _relay_on():
    relay_pin.value(0 if RELAY_ACTIVE_LOW else 1)


def _relay_off():
    relay_pin.value(1 if RELAY_ACTIVE_LOW else 0)


# Initialize relay to off state
_relay_off()

# ========================
# WiFi management
# ========================
STAT_IDLE = getattr(network, "STAT_IDLE", 0)
STAT_CONNECTING = getattr(network, "STAT_CONNECTING", 1)
STAT_GOT_IP = getattr(network, "STAT_GOT_IP", 5)

wlan = network.WLAN(network.STA_IF)
wdt = None
last_ota_check_ms = 0
installed_version = "unknown"


def setup_wifi(max_attempts=20, retry_delay=500):
    """Connect to WiFi, retrying up to max_attempts."""
    if not wlan.active():
        wlan.active(True)
    if wait_for_existing_connection():
        return True
    if wlan.isconnected():
        return True

    print("[WiFi] Connecting to {}...".format(SSID))
    try:
        wlan.connect(SSID, PASSWORD)
    except Exception as exc:
        # Guard against ESP32 "Wifi Internal Error" raising exceptions
        print("[WiFi] Connection start failed:", exc)
        try:
            wlan.active(False)
            time.sleep_ms(200)
            wlan.active(True)
        except Exception as inner_exc:
            print("[WiFi] Failed to reset interface:", inner_exc)
        return False

    attempts = 0
    while not wlan.isconnected() and attempts < max_attempts:
        time.sleep_ms(retry_delay)
        feed_watchdog()
        attempts += 1
        try:
            status = wlan.status()
        except Exception as exc:
            print("[WiFi] Status read failed:", exc)
            status = None
        if status is not None and status < 0:
            print("[WiFi] Internal status error ({}), resetting interface".format(status))
            try:
                wlan.active(False)
                time.sleep_ms(200)
                wlan.active(True)
            except Exception as inner_exc:
                print("[WiFi] Failed to reset interface:", inner_exc)
            return False
        if attempts % 5 == 0:
            print("[WiFi] Attempt {}...".format(attempts))

    if wlan.isconnected():
        print("[WiFi] Connected, IP:", wlan.ifconfig()[0])
        return True

    print("[WiFi] Failed to connect after {} attempts".format(max_attempts))
    return False


def wait_for_existing_connection(max_wait_ms=2000, check_interval_ms=200):
    """Give the interface a moment to reconnect before forcing a new connect."""
    waited_ms = 0
    while waited_ms < max_wait_ms:
        feed_watchdog()
        if wlan.isconnected():
            print("[WiFi] Already connected, IP:", wlan.ifconfig()[0])
            return True

        try:
            status = wlan.status()
        except Exception as exc:
            print("[WiFi] Status read failed:", exc)
            status = None

        if status in (STAT_GOT_IP, STAT_CONNECTING, STAT_IDLE):
            time.sleep_ms(check_interval_ms)
            waited_ms += check_interval_ms
            continue
        break

    return False


def ensure_wifi():
    """Ensure WiFi connection, attempting reconnection if needed."""
    if wlan.isconnected():
        return True
    print("[WiFi] Disconnected, attempting reconnection...")
    return setup_wifi()


# ========================
# Reliability helpers
# ========================


def init_watchdog():
    """Initialize the hardware watchdog so the board reboots if stuck."""
    global wdt
    try:
        wdt = machine.WDT(timeout=WATCHDOG_TIMEOUT_MS)
        print("[System] Watchdog enabled ({} ms)".format(WATCHDOG_TIMEOUT_MS))
    except Exception as exc:
        # In case hardware/watchdog not available, continue without it
        print("[System] Watchdog not available:", exc)


def feed_watchdog():
    if wdt:
        wdt.feed()


# ========================
# Firmware version helpers
# ========================


def load_installed_version():
    """Read the last installed firmware version from disk."""
    try:
        os.stat(FIRMWARE_VERSION_FILE)
    except OSError as exc:
        err = getattr(exc, "errno", exc.args[0] if getattr(exc, "args", None) else None)
        if err == errno.ENOENT:
            print(
                "[OTA] Version file missing, seeding default {}".format(
                    FIRMWARE_VERSION
                )
            )
            save_installed_version(FIRMWARE_VERSION)
            return FIRMWARE_VERSION
        print("[OTA] Could not stat version file:", exc)
        return FIRMWARE_VERSION

    try:
        with open(FIRMWARE_VERSION_FILE, "r") as fp:
            version = fp.read().strip()
            if version:
                return version
        print("[OTA] Version file empty, falling back to default")
        save_installed_version(FIRMWARE_VERSION)
        return FIRMWARE_VERSION
    except OSError as exc:
        err = getattr(exc, "errno", exc.args[0] if getattr(exc, "args", None) else None)
        if err == errno.ENOENT:
            print(
                "[OTA] Version file missing, seeding default {}".format(
                    FIRMWARE_VERSION
                )
            )
            save_installed_version(FIRMWARE_VERSION)
            return FIRMWARE_VERSION
        print("[OTA] Could not read version file:", exc)
    except Exception as exc:
        print("[OTA] Could not read version file:", exc)
    return FIRMWARE_VERSION


def save_installed_version(version):
    """Persist the installed firmware version to disk."""
    try:
        with open(FIRMWARE_VERSION_FILE, "w") as fp:
            fp.write(str(version))
        print("[OTA] Installed version recorded:", version)
    except Exception as exc:
        print("[OTA] Failed to record version:", exc)


# ========================
# API helpers
# ========================

def _headers():
    return {"X-DEVICE-TOKEN": DEVICE_TOKEN}


def _build_url(endpoint):
    return "{}/{}".format(SERVER_BASE_URL.rstrip("/"), endpoint.lstrip("/"))


def send_get_command():
    url = _build_url(COMMAND_ENDPOINT)
    print("[API] Polling:", url)
    response = None
    try:
        response = requests.get(
            url, headers=_headers(), timeout=REQUEST_TIMEOUT_SEC
        )
        if response.status_code != 200:
            print("[API] Unexpected status:", response.status_code)
            return None
        data = response.json()
        print("[API] Response:", data)
        return data
    except Exception as exc:
        print("[API] GET failed:", exc)
        return None
    finally:
        if response:
            response.close()


def send_ack(command_id):
    url = _build_url(ACK_ENDPOINT)
    payload = {"command_id": command_id}
    print("[API] Sending ACK for command {}".format(command_id))
    response = None
    try:
        response = requests.post(
            url,
            headers=_headers(),
            data=json.dumps(payload),
            timeout=REQUEST_TIMEOUT_SEC,
        )
        if response.status_code != 200:
            print("[API] ACK failed, status:", response.status_code)
        else:
            print("[API] ACK success")
    except Exception as exc:
        print("[API] ACK error:", exc)
    finally:
        if response:
            response.close()


def fetch_ota_payload():
    """Fetch OTA payload describing the new firmware."""
    url = _build_url(OTA_ENDPOINT)
    print("[OTA] Checking for updates at:", url)
    response = None
    try:
        response = requests.get(
            url, headers=_headers(), timeout=REQUEST_TIMEOUT_SEC
        )
        if response.status_code != 200:
            print("[OTA] Unexpected status:", response.status_code)
            return None
        data = response.json()
        if not data or not data.get("content"):
            print("[OTA] No update content available")
            return None
        return data
    except Exception as exc:
        print("[OTA] Check failed:", exc)
        return None
    finally:
        if response:
            response.close()


def apply_ota_update(content, version):
    """Write new firmware to disk atomically and reboot."""
    global installed_version
    temp_path = "main.py.new"
    final_path = "main.py"
    try:
        with open(temp_path, "w") as fp:
            fp.write(content)
        os.rename(temp_path, final_path)
        save_installed_version(version)
        installed_version = version
        print("[OTA] Update written, rebooting...")
        time.sleep_ms(RESET_DELAY_MS)
        machine.reset()
    except Exception as exc:
        print("[OTA] Failed to apply update:", exc)
        try:
            os.remove(temp_path)
        except Exception:
            pass


def maybe_check_ota(last_check_ms):
    """Poll OTA endpoint periodically for wireless updates."""
    global installed_version
    if not OTA_ENABLED:
        return last_check_ms

    now = time.ticks_ms()
    if last_check_ms and time.ticks_diff(now, last_check_ms) < OTA_CHECK_INTERVAL_MS:
        return last_check_ms

    payload = fetch_ota_payload()
    if payload and payload.get("content"):
        version = payload.get("version", "unknown")
        if version == installed_version:
            print("[OTA] Already running version {}, skipping".format(version))
            return now
        print("[OTA] Update available: version {}".format(version))
        apply_ota_update(payload["content"], version)
    return now


# ========================
# Relay control
# ========================

def trigger_relay(duration_ms):
    print("[Relay] Activating for {} ms".format(duration_ms))
    _relay_on()
    time.sleep_ms(duration_ms)
    _relay_off()
    print("[Relay] Deactivated")


# ========================
# Main loop
# ========================

def main():
    global last_ota_check_ms
    global installed_version

    init_watchdog()
    setup_wifi()
    installed_version = load_installed_version()
    print("[OTA] Installed firmware version:", installed_version)
    last_ota_check_ms = time.ticks_ms()

    while True:
        feed_watchdog()

        if not ensure_wifi():
            print("[WiFi] Not connected, retrying after delay...")
            time.sleep_ms(POLL_INTERVAL_MS)
            continue

        command = send_get_command()
        if command and command.get("open"):
            duration = int(command.get("pulse_ms", 1000))
            cmd_id = command.get("command_id")
            print("[Command] Open requested: {} ms, id={}".format(duration, cmd_id))
            trigger_relay(duration)
            if cmd_id is not None:
                send_ack(cmd_id)
        else:
            print("[Command] No action")

        last_ota_check_ms = maybe_check_ota(last_ota_check_ms)
        feed_watchdog()
        time.sleep_ms(POLL_INTERVAL_MS)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as exc:
            print("[System] Fatal error, resetting:", exc)
            time.sleep_ms(RESET_DELAY_MS)
            machine.reset()
