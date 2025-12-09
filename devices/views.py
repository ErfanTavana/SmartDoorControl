import json
from datetime import timedelta

from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Count

from access.models import DoorCommand
from accounts.decorators import head_required
from households.utils import get_or_create_head_household
from .models import Device, DeviceFirmware, DeviceLog


def _sanitize_metadata(value):
    """Ensure metadata is JSON serializable before storing it."""

    def convert(item):
        if item is None or isinstance(item, (bool, int, float, str)):
            return item
        if isinstance(item, dict):
            return {str(key): convert(val) for key, val in item.items()}
        if isinstance(item, (list, tuple, set)):
            return [convert(val) for val in item]
        return str(item)

    return convert(value)


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
    level = (payload.get("level") or "info").lower()
    event_type = payload.get("event_type") or payload.get("type") or ""
    firmware_version = payload.get("firmware_version") or payload.get("version") or ""
    metadata = payload.get("metadata") or {}

    if not message:
        return JsonResponse({"error": "Missing log message"}, status=400)

    if not isinstance(metadata, dict):
        metadata = {"value": metadata}

    # Enrich logs with server-side context
    metadata.setdefault("remote_addr", request.META.get("REMOTE_ADDR"))
    metadata.setdefault("user_agent", request.META.get("HTTP_USER_AGENT"))
    metadata = _sanitize_metadata(metadata)

    DeviceLog.objects.create(
        device=device,
        level=level,
        event_type=event_type,
        firmware_version=firmware_version,
        metadata=metadata,
        message=message,
    )

    device.last_seen = timezone.now()
    device.save(update_fields=["last_seen"])
    return JsonResponse({"status": "ok"})


@head_required
def device_logs(request):
    household = get_or_create_head_household(request.user)
    queryset = DeviceLog.objects.filter(device__building=household.building)
    logs = queryset.select_related("device").order_by("-created_at")[:200]

    level_breakdown = (
        queryset.values("level").annotate(count=Count("id")).order_by("level")
    )
    event_breakdown = (
        queryset.values("event_type").annotate(count=Count("id")).order_by("event_type")
    )
    return render(
        request,
        "devices/device_logs.html",
        {
            "household": household,
            "logs": logs,
            "level_breakdown": level_breakdown,
            "event_breakdown": event_breakdown,
        },
    )
