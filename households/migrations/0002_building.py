from django.db import migrations, models
import django.db.models.deletion


def bootstrap_buildings(apps, schema_editor):
    Building = apps.get_model('households', 'Building')
    Household = apps.get_model('households', 'Household')
    for household in Household.objects.all():
        building, _ = Building.objects.get_or_create(title=f"{household.title} Building")
        household.building = building
        household.save(update_fields=['building'])


def noop_reverse(apps, schema_editor):
    # We avoid deleting buildings to preserve data integrity.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('households', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Building',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('address', models.CharField(blank=True, max_length=255)),
            ],
        ),
        migrations.AddField(
            model_name='household',
            name='building',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='households', to='households.building'),
        ),
        migrations.RunPython(bootstrap_buildings, reverse_code=noop_reverse),
        migrations.AlterField(
            model_name='household',
            name='building',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='households', to='households.building'),
        ),
    ]
