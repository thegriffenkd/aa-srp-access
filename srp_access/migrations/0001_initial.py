from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("authentication", "0026_alter_characterownership_user_and_more"),
        ("srp", "0007_alter_srpuserrequest_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="SrpAccessSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("allow_any_public_state", models.BooleanField(default=True)),
                (
                    "required_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="auth.group",
                    ),
                ),
                (
                    "selected_states",
                    models.ManyToManyField(
                        blank=True,
                        related_name="+",
                        to="authentication.state",
                    ),
                ),
            ],
            options={"verbose_name": "restricted SRP settings"},
        ),
        migrations.CreateModel(
            name="ExposedSrpFleet",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("enabled", models.BooleanField(default=True)),
                (
                    "fleet",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="srp_access_exposure",
                        to="srp.srpfleetmain",
                    ),
                ),
            ],
            options={
                "verbose_name": "exposed SRP fleet",
                "verbose_name_plural": "exposed SRP fleets",
                "ordering": ("-fleet__fleet_time", "-pk"),
            },
        ),
    ]
