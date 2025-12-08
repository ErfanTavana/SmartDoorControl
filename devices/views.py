import json

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Device, DeviceFirmware, DeviceLog
from access.models import DoorCommand


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

    device.last_seen = timezone.now()
    device.save(update_fields=["last_seen"])

    command = device.commands.filter(executed=False).order_by("created_at").first()
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
        command = device.commands.get(id=command_id, executed=False)
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

    payload = {"version": firmware.version, "content": firmware.content}
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
