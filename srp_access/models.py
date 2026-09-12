from django.contrib.auth.models import Group
from django.db import models
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel

from allianceauth.authentication.models import State
from allianceauth.srp.models import SrpFleetMain


class SrpAccessSettings(SingletonModel):
    required_group = models.ForeignKey(
        Group,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("required access group"),
    )
    allow_any_public_state = models.BooleanField(
        default=True,
        verbose_name=_("allow any public state"),
        help_text=_(
            "When enabled, users must belong to a State whose public flag is set. "
            "When disabled, users must belong to one of the selected States."
        ),
    )
    selected_states = models.ManyToManyField(
        State,
        blank=True,
        related_name="+",
        verbose_name=_("selected states"),
    )

    class Meta:
        verbose_name = _("restricted SRP settings")

    def __str__(self):
        return str(_("Restricted SRP settings"))


class ExposedSrpFleet(models.Model):
    fleet = models.OneToOneField(
        SrpFleetMain,
        on_delete=models.CASCADE,
        related_name="srp_access_exposure",
        verbose_name=_("built-in SRP fleet"),
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ("-fleet__fleet_time", "-pk")
        verbose_name = _("exposed SRP fleet")
        verbose_name_plural = _("exposed SRP fleets")

    def __str__(self):
        return str(self.fleet)
