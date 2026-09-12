from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class ExposureGroupsMigrationTests(TransactionTestCase):
    migrate_from = ("srp_access", "0002_alter_exposedsrpfleet_fleet_and_more")
    migrate_to = ("srp_access", "0003_exposure_groups")

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps

        group_model = old_apps.get_model("auth", "Group")
        settings_model = old_apps.get_model("srp_access", "SrpAccessSettings")
        fleet_model = old_apps.get_model("srp", "SrpFleetMain")
        exposure_model = old_apps.get_model("srp_access", "ExposedSrpFleet")

        self.group = group_model.objects.create(name="Migration fixture group")
        settings_model.objects.create(required_group=self.group)
        fleet = fleet_model.objects.create(
            fleet_name="Migration fixture fleet",
            fleet_time=timezone.now(),
            fleet_srp_code="MIGRATION01",
        )
        self.exposure = exposure_model.objects.create(fleet=fleet)

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_global_group_is_copied_to_existing_exposures(self):
        exposure_model = self.apps.get_model("srp_access", "ExposedSrpFleet")
        settings_model = self.apps.get_model("srp_access", "SrpAccessSettings")

        exposure = exposure_model.objects.get(pk=self.exposure.pk)

        self.assertTrue(exposure.groups.filter(pk=self.group.pk).exists())
        self.assertNotIn(
            "required_group",
            {field.name for field in settings_model._meta.get_fields()},
        )
