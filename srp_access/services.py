import logging
import math

import requests
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from allianceauth.srp.managers import SRPManager
from allianceauth.srp.models import SrpUserRequest
from allianceauth.srp.providers import (
    get_killmails_killmail_id_killmail_hash,
    get_universe_types_type_id,
)

from . import __version__
from .access import can_use_restricted_srp


logger = logging.getLogger(__name__)

ZKILLBOARD_API_URL = "https://zkillboard.com/api/killID/{killmail_id}/"
ZKILLBOARD_TIMEOUT = (3.05, 10)
KILLMAIL_NOT_AVAILABLE_MESSAGE = (
    "The killmail is not available from zKillboard yet. "
    "Wait at least five minutes after the loss and try again."
)
KILLMAIL_VALIDATION_MESSAGE = (
    "The killmail could not be validated. Check the link and try again."
)


class SrpSubmissionError(Exception):
    """A user-safe submission failure."""


def _get_kill_data(killmail_id):
    """Fetch and validate zKillboard metadata plus the authoritative ESI killmail."""
    expected_killmail_id = int(killmail_id)
    url = ZKILLBOARD_API_URL.format(killmail_id=expected_killmail_id)
    headers = {
        "User-Agent": (
            f"aa-srp-access/{__version__} "
            "(+https://github.com/thegriffenkd/aa-srp-access)"
        ),
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
    }

    try:
        response = requests.get(url, headers=headers, timeout=ZKILLBOARD_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        logger.warning(
            "zKillboard lookup failed for killmail_id=%s reason=request status=%s",
            expected_killmail_id,
            status,
        )
        raise SrpSubmissionError(KILLMAIL_VALIDATION_MESSAGE) from exc

    try:
        payload = response.json()
    except (TypeError, ValueError) as exc:
        logger.warning(
            "zKillboard lookup failed for killmail_id=%s reason=non_json",
            expected_killmail_id,
        )
        raise SrpSubmissionError(KILLMAIL_VALIDATION_MESSAGE) from exc

    if payload == []:
        logger.warning(
            "zKillboard lookup deferred for killmail_id=%s reason=not_available",
            expected_killmail_id,
        )
        raise SrpSubmissionError(KILLMAIL_NOT_AVAILABLE_MESSAGE)

    try:
        if not isinstance(payload, list) or len(payload) != 1:
            raise ValueError("unexpected response container")
        result = payload[0]
        if not isinstance(result, dict):
            raise ValueError("unexpected killmail entry")

        response_killmail_id = result["killmail_id"]
        zkb = result["zkb"]
        killmail_hash = zkb["hash"]
        ship_value = zkb["totalValue"]

        if (
            isinstance(response_killmail_id, bool)
            or not isinstance(response_killmail_id, int)
            or response_killmail_id != expected_killmail_id
        ):
            raise ValueError("mismatched killmail ID")
        if not isinstance(killmail_hash, str) or len(killmail_hash) != 40:
            raise ValueError("invalid killmail hash")
        if (
            isinstance(ship_value, bool)
            or not isinstance(ship_value, (int, float))
            or not math.isfinite(ship_value)
            or ship_value < 0
        ):
            raise ValueError("invalid total value")
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning(
            "zKillboard lookup failed for killmail_id=%s reason=malformed",
            expected_killmail_id,
        )
        raise SrpSubmissionError(KILLMAIL_VALIDATION_MESSAGE) from exc

    try:
        killmail = get_killmails_killmail_id_killmail_hash(
            killmail_id=response_killmail_id,
            killmail_hash=killmail_hash,
        )
    except Exception as exc:
        logger.warning(
            "ESI killmail lookup failed for killmail_id=%s reason=request",
            expected_killmail_id,
        )
        raise SrpSubmissionError(KILLMAIL_VALIDATION_MESSAGE) from exc

    try:
        ship_type_id = killmail.victim.ship_type_id
        victim_id = killmail.victim.character_id
        if not isinstance(ship_type_id, int) or ship_type_id <= 0:
            raise ValueError("invalid victim ship type")
        if not isinstance(victim_id, int) or victim_id <= 0:
            raise ValueError("invalid victim character")
    except (AttributeError, TypeError, ValueError) as exc:
        logger.warning(
            "ESI killmail lookup failed for killmail_id=%s reason=incomplete",
            expected_killmail_id,
        )
        raise SrpSubmissionError(KILLMAIL_VALIDATION_MESSAGE) from exc

    return ship_type_id, ship_value, victim_id


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
        ship_type_id, ship_value, victim_id = _get_kill_data(killmail_id)
        item_type = get_universe_types_type_id(ship_type_id)
    except SrpSubmissionError:
        raise
    except Exception as exc:
        logger.warning(
            "Killmail validation failed for killmail_id=%s reason=ship_type",
            killmail_id,
        )
        raise SrpSubmissionError(KILLMAIL_VALIDATION_MESSAGE) from exc

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
