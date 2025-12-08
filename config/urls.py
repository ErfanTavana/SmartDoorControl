from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", account_views.login_view),
    path("accounts/", include("accounts.urls")),
    path("households/", include("households.urls")),
    path("", include("access.urls")),
    path("", include("devices.urls")),
]
