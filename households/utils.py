from .models import Building, Household


def get_or_create_head_household(user):
    household, created = Household.objects.get_or_create(
        head=user,
        defaults={
            "title": f"{user.username}'s Home",
            "building": Building.objects.create(title=f"{user.username}'s Building"),
        },
    )
    if created and household.building is None:
        household.building = Building.objects.create(title=f"{user.username}'s Building")
        household.save(update_fields=["building"])
    return household
