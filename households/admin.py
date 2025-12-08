from django.contrib import admin

from .models import Building, Household, MemberProfile


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("title", "address")
    search_fields = ("title", "address")


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("title", "head")
    search_fields = ("title", "head__username")


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "household", "allowed_from_time", "allowed_to_time", "active")
    list_filter = ("active", "household")
    search_fields = ("user__username",)
