from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import head_required
from .forms import MemberCreationForm, MemberProfileForm
from .models import Household, MemberProfile
from .utils import get_or_create_head_household

User = get_user_model()


@head_required
def head_dashboard(request):
    household = get_or_create_head_household(request.user)
    member_count = household.members.count()
    device_count = household.building.devices.count()
    return render(
        request,
        "households/head_dashboard.html",
        {"household": household, "member_count": member_count, "device_count": device_count},
    )


@head_required
def member_list(request):
    household = get_or_create_head_household(request.user)
    members = household.members.select_related("user").all()
    return render(request, "households/member_list.html", {"household": household, "members": members})


@head_required
def member_create(request):
    household = get_or_create_head_household(request.user)
    form = MemberCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save(household)
        messages.success(request, "Member created")
        return redirect("households:member_list")
    return render(request, "households/member_form.html", {"form": form, "household": household})


@head_required
def member_edit(request, member_id):
    household = get_or_create_head_household(request.user)
    profile = get_object_or_404(MemberProfile, id=member_id, household=household)
    form = MemberProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Member updated")
        return redirect("households:member_list")
    return render(request, "households/member_form.html", {"form": form, "household": household, "editing": True})


@head_required
def member_delete(request, member_id):
    household = get_or_create_head_household(request.user)
    profile = get_object_or_404(MemberProfile, id=member_id, household=household)
    user = profile.user
    profile.delete()
    user.delete()
    messages.success(request, "Member removed")
    return redirect("households:member_list")
