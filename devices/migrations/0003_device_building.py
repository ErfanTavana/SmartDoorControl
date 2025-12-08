from django.db import migrations, models
import django.db.models.deletion


def migrate_device_building(apps, schema_editor):
    Device = apps.get_model('devices', 'Device')
    Household = apps.get_model('households', 'Household')
    for device in Device.objects.all():
        if hasattr(device, 'household_id') and device.household_id:
            try:
                household = Household.objects.get(id=device.household_id)
                device.building_id = household.building_id
                device.save(update_fields=['building'])
            except Household.DoesNotExist:
                continue


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('households', '0002_building'),
        ('devices', '0002_alter_device_api_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='building',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='devices', to='households.building'),
        ),
        migrations.RunPython(migrate_device_building, reverse_code=noop_reverse),
        migrations.RemoveField(
            model_name='device',
            name='household',
        ),
        migrations.AlterField(
            model_name='device',
            name='building',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='devices', to='households.building'),
        ),
    ]
