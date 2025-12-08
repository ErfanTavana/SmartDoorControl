from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.decorators import head_required
from devices.models import Device
from households.models import Building, Household, MemberProfile
from .models import AccessLog, DoorCommand


@login_required
def member_panel(request):
    user = request.user
    if user.is_head:
        household = Household.objects.filter(head=user).first()
        if not household:
            household = Household.objects.create(
                head=user,
                title=f"{user.username}'s Home",
                building=Building.objects.create(title=f"{user.username}'s Building"),
            )
        member_profile = None
    else:
        member_profile = getattr(user, "member_profile", None)
        household = member_profile.household if member_profile else None

    if request.method == "POST":
        if not household:
            messages.error(request, "No household configured.")
            return redirect("access:member_panel")
        device = household.building.devices.first() if household else None
        if not device:
            messages.error(request, "No device registered for this building.")
            return redirect("access:member_panel")

        if user.is_head:
            _create_command(user, household, device)
            messages.success(request, "Door command queued for your device.")
        else:
            if not member_profile:
                messages.error(request, "No member profile configured.")
                return redirect("access:member_panel")
            allowed, reason = _member_is_allowed(member_profile)
            if allowed:
                _create_command(user, household, device)
                messages.success(request, "Door command queued.")
            else:
                AccessLog.objects.create(
                    user=user, household=household, status=AccessLog.Status.DENIED, reason=reason
                )
                messages.error(request, reason)
        return redirect("access:member_panel")

    return render(request, "access/member_panel.html", {"household": household, "member_profile": member_profile})


def _member_is_allowed(member_profile: MemberProfile):
    if not member_profile.active:
        return False, "Access disabled."
    now = timezone.localtime().time()
    if not (member_profile.allowed_from_time <= now <= member_profile.allowed_to_time):
        return False, "Outside allowed schedule."
    return True, ""


def _create_command(user, household, device: Device):
    DoorCommand.objects.create(device=device, requested_by=user)
    AccessLog.objects.create(user=user, household=household, status=AccessLog.Status.SUCCESS, reason="Door open")


@head_required
def access_logs(request):
    household, _ = Household.objects.get_or_create(
        head=request.user, defaults={"title": f"{request.user.username}'s Home"}
    )
    logs = household.access_logs.select_related("user").order_by("-timestamp")[:100]
    return render(request, "access/access_logs.html", {"logs": logs, "household": household})
