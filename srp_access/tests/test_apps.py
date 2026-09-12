from django.test import SimpleTestCase

from srp_access import __version__
from srp_access.apps import SrpAccessConfig


class SrpAccessConfigTests(SimpleTestCase):
    def test_admin_app_heading_includes_package_version(self):
        self.assertEqual(
            str(SrpAccessConfig.verbose_name),
            f"Restricted SRP access v{__version__}",
        )
