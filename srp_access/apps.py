from django.apps import AppConfig
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from . import __version__


class SrpAccessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "srp_access"
    verbose_name = format_lazy("{} v{}", _("Restricted SRP access"), __version__)
