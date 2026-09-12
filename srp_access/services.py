from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from allianceauth.srp.managers import SRPManager
from allianceauth.srp.models import SrpUserRequest
from allianceauth.srp.providers import get_universe_types_type_id

from .access import can_use_restricted_srp


class SrpSubmissionError(Exception):
    """A user-safe submission failure."""


def create_builtin_srp_request(*, user, fleet, killboard_link, additional_info=""):
    """Validate a restricted submission and create a normal built-in SRP request."""
    if not can_use_restricted_srp(user, fleet):
        raise PermissionDenied

    killmail_id = SRPManager.get_kill_id(killboard_link=killboard_link)
    if not killmail_id:
        raise SrpSubmissionError("The killmail link does not contain a killmail ID.")

    if SrpUserRequest.objects.filter(
        killboard_link__icontains=f"/kill/{killmail_id}"
    ).exists():
        raise SrpSubmissionError("This killmail has already been submitted.")

    try:
        character = user.profile.main_character
    except AttributeError as exc:
        raise SrpSubmissionError("Your account has no main character configured.") from exc

    if character is None:
        raise SrpSubmissionError("Your account has no main character configured.")

    try:
        ship_type_id, ship_value, victim_id = SRPManager.get_kill_data(killmail_id)
        item_type = get_universe_types_type_id(ship_type_id)
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise SrpSubmissionError(
            "The killmail could not be validated. Check the link and try again."
        ) from exc

    if not user.character_ownerships.filter(character__character_id=str(victim_id)).exists():
        raise SrpSubmissionError(
            "The victim character is not registered to your Alliance Auth account."
        )

    with transaction.atomic():
        if SrpUserRequest.objects.filter(
            killboard_link__icontains=f"/kill/{killmail_id}"
        ).exists():
            raise SrpSubmissionError("This killmail has already been submitted.")

        return SrpUserRequest.objects.create(
            killboard_link=killboard_link,
            additional_info=additional_info,
            character=character,
            srp_fleet_main=fleet,
            srp_ship_name=item_type.name,
            kb_total_loss=int(ship_value),
            post_time=timezone.now(),
        )
