import json
from datetime import timedelta

from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from access.models import DoorCommand
from accounts.decorators import head_required
from households.utils import get_or_create_head_household
from .models import Device, DeviceFirmware, DeviceLog


def _get_device_from_request(request):
    token = request.headers.get("X-DEVICE-TOKEN")
    if not token:
        return None
    try:
        return Device.objects.get(api_token=token)
    except Device.DoesNotExist:
        return None


@require_GET
@csrf_exempt
def poll_command(request):
    device = _get_device_from_request(request)
    if not device:
        return JsonResponse({"error": "Invalid token"}, status=401)

    now = timezone.now()
    device.last_seen = now
    device.save(update_fields=["last_seen"])

    expiration_cutoff = now - timedelta(seconds=15)
    expired_commands = device.commands.filter(
        executed=False, expired=False, created_at__lt=expiration_cutoff
    )
    if expired_commands.exists():
        expired_commands.update(expired=True, executed_at=now)

    command = (
        device.commands.filter(executed=False, expired=False)
        .order_by("created_at")
        .first()
    )
    if not command:
        return JsonResponse({"open": False})

    return JsonResponse({"open": True, "command_id": command.id, "pulse_ms": 1000})


@require_POST
@csrf_exempt
def ack_command(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        payload = {}

    device = _get_device_from_request(request)
    if not device:
        return JsonResponse({"error": "Invalid token"}, status=401)

    command_id = payload.get("command_id")
    try:
        command = device.commands.get(id=command_id, executed=False, expired=False)
    except DoorCommand.DoesNotExist:
        return JsonResponse({"error": "Command not found"}, status=404)

    command.executed = True
    command.executed_at = timezone.now()
    command.save(update_fields=["executed", "executed_at"])

    return JsonResponse({"status": "ok"})


@require_GET
@csrf_exempt
def firmware_payload(request):
    device = _get_device_from_request(request)
    if not device:
        return JsonResponse({"error": "Invalid token"}, status=401)

    try:
        firmware = device.firmware
    except DeviceFirmware.DoesNotExist:
        return JsonResponse({}, status=200)

    payload = {
        "version": firmware.version,
        "content": firmware.content,
        "checksum": firmware.checksum,
        "config": firmware.config,
        "config_version": firmware.config_version,
        "config_checksum": firmware.config_checksum,
    }
    return JsonResponse(payload)


@require_POST
@csrf_exempt
def ingest_log(request):
    device = _get_device_from_request(request)
    if not device:
        return JsonResponse({"error": "Invalid token"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        payload = {}

    message = payload.get("message") or payload.get("log")
    level = payload.get("level", "info")

    if not message:
        return JsonResponse({"error": "Missing log message"}, status=400)

    DeviceLog.objects.create(device=device, level=level, message=message)
    return JsonResponse({"status": "ok"})


@head_required
def device_logs(request):
    household = get_or_create_head_household(request.user)
    logs = (
        DeviceLog.objects.filter(device__building=household.building)
        .select_related("device")
        .order_by("-created_at")[:100]
    )
    return render(
        request,
        "devices/device_logs.html",
        {"household": household, "logs": logs},
    )
