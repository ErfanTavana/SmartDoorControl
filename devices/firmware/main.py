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
import webrepl

try:
    import uhashlib as hashlib
except ImportError:  # pragma: no cover - desktop dev environment
    import hashlib

try:
    import urequests as requests
except ImportError:  # Fallback for environments that alias urequests
    import requests

# ========================
# Configuration
# ========================
# Define WiFi networks in priority order.
# Each entry should be a dictionary with keys:
# - ssid: SSID string
# - password: network password
# - priority: lower numbers indicate higher priority
WIFI_NETWORKS = [
    {"ssid": "1283", "password": "0928007634", "priority": 1},
    {"ssid": "ErfanT", "password": "0928007634", "priority": 2},
    {"ssid": "LTE_ROUTER", "password": "96cLvZ7gn9", "priority": 3},

]
SERVER_BASE_URL = "https://erfantavanasmartdoor.pythonanywhere.com/"  # No trailing slash
DEVICE_TOKEN = "nm5bbP3TA4qHpi2DrBqkcaDgmcFEIvwScv1IedyklPA"
RELAY_GPIO_PIN = 16
RELAY_ACTIVE_LOW = True  # Set to True if the relay is active-low
POLL_INTERVAL_MS = 5000
COMMAND_ENDPOINT = "/api/device/command/"
ACK_ENDPOINT = "/api/device/command/ack/"
LOG_ENDPOINT = "/api/device/logs/"
OTA_ENABLED = True
OTA_ENDPOINT = "/api/device/firmware/"
OTA_CHECK_INTERVAL_MS = 60000  # 1 minutes
FIRMWARE_VERSION = "1.0.0"
FIRMWARE_VERSION_FILE = "firmware_version.txt"
FIRMWARE_CHECKSUM_FILE = "firmware_checksum.txt"
CONFIG_FILE = "device_config.json"
CONFIG_VERSION = "1.0.0"
CONFIG_VERSION_FILE = "config_version.txt"
CONFIG_CHECKSUM_FILE = "config_checksum.txt"
VERSION_LOG_INTERVAL_MS = 60000  # 1 minute
WATCHDOG_TIMEOUT_MS = 15000
RESET_DELAY_MS = 2000
# HTTP request timeout (in seconds). Must remain comfortably below WATCHDOG_TIMEOUT_MS
# because network requests are blocking and the watchdog is only fed between calls.
REQUEST_TIMEOUT_SEC = 10
# Enable the built-in WebREPL server to inspect logs/files over WiFi without USB.
WEBREPL_ENABLED = True
WEBREPL_PASSWORD = "smartdoor"

# ========================
# Hardware setup
# ========================
relay_pin = None


def _relay_on():
    """Activate relay using software open-drain (output low = ON)."""
    global relay_pin
    relay_pin = machine.Pin(RELAY_GPIO_PIN, machine.Pin.OUT)
    relay_pin.value(0)


def _relay_off():
    """Deactivate relay by floating the pin (input/high-Z = OFF)."""
    global relay_pin
    relay_pin = machine.Pin(RELAY_GPIO_PIN, machine.Pin.IN, pull=None)


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
installed_config_version = "unknown"
last_version_log_ms = 0
boot_log_sent = False
webrepl_started = False
boot_time_ms = time.ticks_ms()


def _decode_ssid(raw_ssid):
    try:
        return raw_ssid.decode() if isinstance(raw_ssid, bytes) else str(raw_ssid)
    except Exception:
        return str(raw_ssid)


def _configured_networks_by_priority():
    return sorted(WIFI_NETWORKS, key=lambda net: net.get("priority", 1000))


def _available_configured_networks():
    """Return configured networks that are currently visible, sorted by priority."""
    try:
        scan_results = wlan.scan()
    except Exception as exc:
        print("[WiFi] Scan failed, using configured order:", exc)
        return _configured_networks_by_priority()

    available_ssids = set()
    for result in scan_results:
        if not result:
            continue
        available_ssids.add(_decode_ssid(result[0]))

    prioritized = _configured_networks_by_priority()
    visible = [net for net in prioritized if net.get("ssid") in available_ssids]
    if visible:
        return visible

    print("[WiFi] No configured networks visible, using full list")
    return prioritized


def _connect_to_network(ssid, password, max_attempts, retry_delay):
    print("[WiFi] Connecting to {}...".format(ssid))
    try:
        # Best-effort disconnect to clear any previous session
        if hasattr(wlan, "disconnect"):
            try:
                wlan.disconnect()
            except Exception:
                pass
        wlan.connect(ssid, password)
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
            print(
                "[WiFi] Internal status error ({}), resetting interface".format(status)
            )
            try:
                wlan.active(False)
                time.sleep_ms(200)
                wlan.active(True)
            except Exception as inner_exc:
                print("[WiFi] Failed to reset interface:", inner_exc)
            return False
        if attempts % 3 == 0:
            print("[WiFi] Attempt {}...".format(attempts))

    if wlan.isconnected():
        print("[WiFi] Connected to {} with IP {}".format(ssid, wlan.ifconfig()[0]))
        return True

    print("[WiFi] Failed to connect to {} after {} attempts".format(ssid, max_attempts))
    return False


def setup_wifi(max_attempts=20, retry_delay=500):
    """Connect to the best available WiFi based on configured priorities."""
    if not wlan.active():
        wlan.active(True)
    if wait_for_existing_connection():
        return True
    if wlan.isconnected():
        return True

    candidate_networks = _available_configured_networks()
    if not candidate_networks:
        print("[WiFi] No configured networks available")
        return False

    per_network_attempts = max(1, min(max_attempts, 5))
    for network in candidate_networks:
        ssid = network.get("ssid")
        password = network.get("password", "")
        if not ssid:
            continue
        if _connect_to_network(ssid, password, per_network_attempts, retry_delay):
            return True

    print("[WiFi] Failed to connect to any configured network")
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


def maybe_start_webrepl():
    """Start WebREPL once WiFi is connected to allow wireless access."""
    global webrepl_started

    if webrepl_started or not WEBREPL_ENABLED:
        return

    if WEBREPL_PASSWORD and len(WEBREPL_PASSWORD) < 4:
        print("[WebREPL] Password must be at least 4 characters; skipping start")
        return

    if not wlan.isconnected():
        return

    try:
        if WEBREPL_PASSWORD:
            webrepl.start(password=WEBREPL_PASSWORD)
        else:
            webrepl.start()
        webrepl_started = True
        print("[WebREPL] Started on {} (connect with ws://{}:8266)".format(
            wlan.ifconfig()[0], wlan.ifconfig()[0]
        ))
    except Exception as exc:
        print("[WebREPL] Failed to start:", exc)


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
# Firmware/config helpers
# ========================


def _read_text_file(path, default_value=None):
    try:
        with open(path, "r") as fp:
            content = fp.read().strip()
            return content if content else default_value
    except OSError as exc:
        err = getattr(exc, "errno", exc.args[0] if getattr(exc, "args", None) else None)
        if err == errno.ENOENT:
            return default_value
        print("[OTA] Could not read {}: {}".format(path, exc))
        return default_value
    except Exception as exc:
        print("[OTA] Could not read {}: {}".format(path, exc))
        return default_value


def _write_text_file(path, value):
    try:
        with open(path, "w") as fp:
            fp.write(value)
        return True
    except Exception as exc:
        print("[OTA] Could not write {}: {}".format(path, exc))
        return False


def calculate_checksum(content):
    if content is None:
        return ""
    try:
        digest = hashlib.sha256()
        digest.update(content.encode("utf-8"))
        try:
            return digest.hexdigest()
        except AttributeError:
            return "".join("{:02x}".format(b) for b in digest.digest())
    except Exception as exc:
        print("[OTA] Failed to hash content:", exc)
        return ""


def checksum_matches(content, expected_checksum):
    if not expected_checksum:
        return True
    calculated = calculate_checksum(content)
    if calculated.lower() != expected_checksum.lower():
        print(
            "[OTA] Checksum mismatch. Expected {}, got {}".format(
                expected_checksum, calculated
            )
        )
        return False
    return True


def load_installed_version():
    """Read the last installed firmware version from disk."""
    version = _read_text_file(FIRMWARE_VERSION_FILE, FIRMWARE_VERSION)
    if version is None:
        version = FIRMWARE_VERSION
    if version == FIRMWARE_VERSION:
        _write_text_file(FIRMWARE_VERSION_FILE, str(version))
    return version


def save_installed_version(version):
    """Persist the installed firmware version to disk."""
    try:
        with open(FIRMWARE_VERSION_FILE, "w") as fp:
            fp.write(str(version))
        print("[OTA] Installed version recorded:", version)
    except Exception as exc:
        print("[OTA] Failed to record version:", exc)


def load_installed_config_version():
    """Read the last applied configuration version."""
    version = _read_text_file(CONFIG_VERSION_FILE, CONFIG_VERSION)
    if version is None:
        version = CONFIG_VERSION
    if version == CONFIG_VERSION:
        _write_text_file(CONFIG_VERSION_FILE, str(version))
    return version


def save_installed_config_version(version):
    """Persist the installed configuration version to disk."""
    if _write_text_file(CONFIG_VERSION_FILE, str(version)):
        print("[OTA] Installed config version recorded:", version)


def save_checksum(path, checksum):
    if not checksum:
        return
    _write_text_file(path, checksum)


# ========================
# API helpers
# ========================

def _headers():
    headers = {"X-DEVICE-TOKEN": DEVICE_TOKEN}
    if installed_version:
        headers["X-FIRMWARE-VERSION"] = str(installed_version)
    if installed_config_version:
        headers["X-CONFIG-VERSION"] = str(installed_config_version)
    return headers


def _build_url(endpoint):
    return "{}/{}".format(SERVER_BASE_URL.rstrip("/"), endpoint.lstrip("/"))


def send_get_command():
    url = _build_url(COMMAND_ENDPOINT)
    print("[API] Polling:", url)
    response = None
    try:
        feed_watchdog()
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
        feed_watchdog()
        if response:
            response.close()


def send_ack(command_id):
    url = _build_url(ACK_ENDPOINT)
    payload = {"command_id": command_id}
    print("[API] Sending ACK for command {}".format(command_id))
    response = None
    try:
        feed_watchdog()
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
        feed_watchdog()
        if response:
            response.close()


def _uptime_seconds():
    try:
        return int(time.ticks_diff(time.ticks_ms(), boot_time_ms) / 1000)
    except Exception:
        return 0


def _wifi_snapshot():
    info = {"connected": False}
    try:
        info["connected"] = wlan.isconnected()
    except Exception:
        pass
    try:
        info["ip"] = wlan.ifconfig()[0]
    except Exception:
        pass
    try:
        info["rssi"] = wlan.status("rssi")
    except Exception:
        pass
    try:
        ssid = wlan.config("essid")
        if isinstance(ssid, bytes):
            ssid = ssid.decode()
        info["ssid"] = ssid
    except Exception:
        pass
    return info


def _build_metadata(extra=None):
    metadata = {
        "uptime_seconds": _uptime_seconds(),
        "wifi": _wifi_snapshot(),
        "config_version": installed_config_version,
    }
    if isinstance(extra, dict):
        metadata.update(extra)
    elif extra is not None:
        metadata["detail"] = extra
    return metadata


def send_log(message, level="info", event_type="general", metadata=None):
    """Send a device log message to the server."""
    url = _build_url(LOG_ENDPOINT)
    payload = {
        "message": message,
        "level": level,
        "event_type": event_type,
        "firmware_version": installed_version,
        "metadata": _build_metadata(metadata),
    }
    response = None
    print("[Log] Sending {}: {}".format(level.upper(), message))
    try:
        feed_watchdog()
        response = requests.post(
            url,
            headers=_headers(),
            data=json.dumps(payload),
            timeout=REQUEST_TIMEOUT_SEC,
        )
        if response.status_code != 200:
            print("[Log] Failed, status:", response.status_code)
            return False
        print("[Log] Sent successfully")
        return True
    except Exception as exc:
        print("[Log] Error sending log:", exc)
        return False
    finally:
        feed_watchdog()
        if response:
            response.close()


def fetch_ota_payload():
    """Fetch OTA payload describing the new firmware."""
    url = _build_url(OTA_ENDPOINT)
    print("[OTA] Checking for updates at:", url)
    response = None
    try:
        feed_watchdog()
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
        feed_watchdog()
        if response:
            response.close()


def apply_ota_update(content, version, checksum=None):
    """Write new firmware to disk atomically and reboot."""
    global installed_version

    if not checksum_matches(content, checksum):
        send_log(
            "OTA firmware checksum mismatch for version {}".format(version),
            level="error",
            event_type="ota",
            metadata={"version": version, "checksum": checksum},
        )
        return False

    temp_path = "main.py.new"
    final_path = "main.py"
    try:
        with open(temp_path, "w") as fp:
            fp.write(content)
        os.rename(temp_path, final_path)
        save_installed_version(version)
        save_checksum(FIRMWARE_CHECKSUM_FILE, checksum)
        installed_version = version
        send_log(
            "Firmware {} installed via OTA".format(version),
            event_type="ota",
            metadata={"version": version, "checksum": checksum},
        )
        print("[OTA] Update written, rebooting...")
        time.sleep_ms(RESET_DELAY_MS)
        machine.reset()
        return True
    except Exception as exc:
        print("[OTA] Failed to apply update:", exc)
        send_log(
            "OTA apply failed for version {}".format(version),
            level="error",
            event_type="ota",
            metadata={"version": version, "checksum": checksum},
        )
        try:
            os.remove(temp_path)
        except Exception:
            pass
    return False


def apply_config_update(content, version, checksum=None):
    """Persist configuration updates separately from firmware."""
    global installed_config_version

    if not content:
        return False

    if not version:
        version = CONFIG_VERSION

    if not checksum_matches(content, checksum):
        send_log(
            "OTA config checksum mismatch for version {}".format(version),
            level="error",
            event_type="config",
            metadata={"version": version, "checksum": checksum},
        )
        return False

    try:
        with open(CONFIG_FILE, "w") as fp:
            fp.write(content)
        save_installed_config_version(version)
        save_checksum(CONFIG_CHECKSUM_FILE, checksum)
        installed_config_version = version
        send_log(
            "Config {} applied via OTA".format(version),
            event_type="config",
            metadata={"version": version, "checksum": checksum},
        )
        print("[OTA] Configuration updated to {}".format(version))
        return True
    except Exception as exc:
        print("[OTA] Failed to apply configuration:", exc)
        send_log(
            "OTA config apply failed for {}".format(version),
            level="error",
            event_type="config",
            metadata={"version": version, "checksum": checksum},
        )
    return False


def maybe_check_ota(last_check_ms):
    """Poll OTA endpoint periodically for wireless updates."""
    global installed_version
    global installed_config_version
    if not OTA_ENABLED:
        return last_check_ms

    now = time.ticks_ms()
    if last_check_ms and time.ticks_diff(now, last_check_ms) < OTA_CHECK_INTERVAL_MS:
        return last_check_ms

    payload = fetch_ota_payload()
    if not payload:
        return now

    firmware_content = payload.get("content")
    firmware_version = payload.get("version", "unknown")
    firmware_checksum = payload.get("checksum")
    config_content = payload.get("config")
    config_version = payload.get("config_version") or ""
    config_checksum = payload.get("config_checksum")

    if firmware_content:
        if firmware_version == installed_version:
            print("[OTA] Already running version {}, skipping".format(firmware_version))
        else:
            print("[OTA] Update available: version {}".format(firmware_version))
            send_log(
                "OTA firmware available ({})".format(firmware_version),
                event_type="ota",
                metadata={"version": firmware_version},
            )
            apply_ota_update(firmware_content, firmware_version, firmware_checksum)

    if config_content:
        if config_version and config_version == installed_config_version:
            print(
                "[OTA] Configuration already at version {}, skipping".format(
                    config_version
                )
            )
        else:
            print("[OTA] Applying configuration version {}".format(config_version))
            apply_config_update(config_content, config_version, config_checksum)

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
    global installed_config_version
    global last_version_log_ms
    global boot_log_sent

    init_watchdog()
    setup_wifi()
    installed_version = load_installed_version()
    installed_config_version = load_installed_config_version()
    print("[OTA] Installed firmware version:", installed_version)
    print("[OTA] Installed config version:", installed_config_version)
    # Force an OTA check immediately after boot so new firmware is applied
    # without waiting for the periodic interval.
    last_ota_check_ms = 0

    while True:
        feed_watchdog()

        if not ensure_wifi():
            print("[WiFi] Not connected, retrying after delay...")
            time.sleep_ms(POLL_INTERVAL_MS)
            continue

        maybe_start_webrepl()

        if not boot_log_sent:
            if send_log(
                "Firmware {} (config {}) started with IP {}".format(
                    installed_version, installed_config_version, wlan.ifconfig()[0]
                ),
                event_type="boot",
                metadata={"ip": wlan.ifconfig()[0]},
            ):
                boot_log_sent = True

        command = send_get_command()
        if command and command.get("open"):
            duration = int(command.get("pulse_ms", 1000))
            cmd_id = command.get("command_id")
            print("[Command] Open requested: {} ms, id={}".format(duration, cmd_id))
            trigger_relay(duration)
            send_log(
                "Relay triggered for {} ms (command {})".format(
                    duration, cmd_id if cmd_id is not None else "unknown"
                ),
                event_type="command",
                metadata={"duration_ms": duration, "command_id": cmd_id},
            )
            if cmd_id is not None:
                send_ack(cmd_id)
        else:
            print("[Command] No action")

        last_ota_check_ms = maybe_check_ota(last_ota_check_ms)
        now_ms = time.ticks_ms()
        if (
            not last_version_log_ms
            or time.ticks_diff(now_ms, last_version_log_ms) >= VERSION_LOG_INTERVAL_MS
        ):
            send_log(
                "Running firmware {} (config {})".format(
                    installed_version, installed_config_version
                ),
                event_type="heartbeat",
            )
            last_version_log_ms = now_ms
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
