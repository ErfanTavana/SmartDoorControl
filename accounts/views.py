from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.urls import reverse


def login_view(request):
    if request.user.is_authenticated:
        return redirect(role_redirect(request.user))

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect(role_redirect(user))

    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect(reverse("accounts:login"))


def role_redirect(user):
    if getattr(user, "is_head", False):
        return reverse("households:head_dashboard")
    return reverse("access:member_panel")
