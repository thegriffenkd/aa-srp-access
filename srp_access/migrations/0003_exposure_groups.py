from django.db import migrations, models


def copy_required_group_to_exposures(apps, schema_editor):
    settings_model = apps.get_model("srp_access", "SrpAccessSettings")
    exposure_model = apps.get_model("srp_access", "ExposedSrpFleet")
    settings = settings_model.objects.first()
    if settings is None or settings.required_group_id is None:
        return

    for exposure in exposure_model.objects.all().iterator():
        exposure.groups.add(settings.required_group_id)


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("srp_access", "0002_alter_exposedsrpfleet_fleet_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="exposedsrpfleet",
            name="groups",
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    "Users must belong to at least one selected group to see this "
                    "fleet. An exposure without groups is inaccessible."
                ),
                related_name="+",
                to="auth.group",
                verbose_name="access groups",
            ),
        ),
        migrations.RunPython(
            copy_required_group_to_exposures,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="srpaccesssettings",
            name="required_group",
        ),
    ]
