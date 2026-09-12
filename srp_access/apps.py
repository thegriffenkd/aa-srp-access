from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SrpAccessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "srp_access"
    verbose_name = _("Restricted SRP access")
