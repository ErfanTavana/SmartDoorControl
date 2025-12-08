"""
MicroPython firmware for ESP32-S3 door controller.

Features:
- WiFi connection with reconnection handling.
- Polling a Django backend for open-door commands.
- Relay control with configurable active polarity.
- Safe error handling for network and API issues.
"""

import json
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
SSID = "YOUR_WIFI_SSID"
PASSWORD = "YOUR_WIFI_PASSWORD"
SERVER_BASE_URL = "http://example.com"  # No trailing slash
DEVICE_TOKEN = "replace-with-device-token"
RELAY_GPIO_PIN = 5
RELAY_ACTIVE_LOW = False  # Set to True if the relay is active-low
POLL_INTERVAL_MS = 5000
COMMAND_ENDPOINT = "/api/device/command/"
ACK_ENDPOINT = "/api/device/command/ack/"

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
wlan = network.WLAN(network.STA_IF)


def setup_wifi(max_attempts=20, retry_delay=500):
    """Connect to WiFi, retrying up to max_attempts."""
    if not wlan.active():
        wlan.active(True)
    if wlan.isconnected():
        return True

    print("[WiFi] Connecting to {}...".format(SSID))
    wlan.connect(SSID, PASSWORD)

    attempts = 0
    while not wlan.isconnected() and attempts < max_attempts:
        time.sleep_ms(retry_delay)
        attempts += 1
        if attempts % 5 == 0:
            print("[WiFi] Attempt {}...".format(attempts))

    if wlan.isconnected():
        print("[WiFi] Connected, IP:", wlan.ifconfig()[0])
        return True

    print("[WiFi] Failed to connect after {} attempts".format(max_attempts))
    return False


def ensure_wifi():
    """Ensure WiFi connection, attempting reconnection if needed."""
    if wlan.isconnected():
        return True
    print("[WiFi] Disconnected, attempting reconnection...")
    return setup_wifi()


# ========================
# API helpers
# ========================

def _headers():
    return {"X-DEVICE-TOKEN": DEVICE_TOKEN}


def send_get_command():
    url = SERVER_BASE_URL + COMMAND_ENDPOINT
    print("[API] Polling:", url)
    response = None
    try:
        response = requests.get(url, headers=_headers())
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
    url = SERVER_BASE_URL + ACK_ENDPOINT
    payload = {"command_id": command_id}
    print("[API] Sending ACK for command {}".format(command_id))
    response = None
    try:
        response = requests.post(url, headers=_headers(), data=json.dumps(payload))
        if response.status_code != 200:
            print("[API] ACK failed, status:", response.status_code)
        else:
            print("[API] ACK success")
    except Exception as exc:
        print("[API] ACK error:", exc)
    finally:
        if response:
            response.close()


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
    setup_wifi()
    while True:
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

        time.sleep_ms(POLL_INTERVAL_MS)


if __name__ == "__main__":
    main()
