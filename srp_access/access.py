from django.core.exceptions import ObjectDoesNotExist

from allianceauth.srp.models import SrpFleetMain

from .models import ExposedSrpFleet, SrpAccessSettings


def get_access_settings():
    """Return configured settings without creating database state during requests."""
    return SrpAccessSettings.objects.first()


def user_has_eligible_state(user, settings=None):
    if not getattr(user, "is_authenticated", False):
        return False

    try:
        state = user.profile.state
    except ObjectDoesNotExist:
        return False

    if state is None:
        return False

    settings = settings or get_access_settings()
    if settings is None:
        return False

    if settings.allow_any_public_state:
        return bool(state.public)

    return settings.selected_states.filter(pk=state.pk).exists()


def user_has_exposed_fleet(user, fleet=None):
    if not getattr(user, "is_authenticated", False):
        return False

    exposures = ExposedSrpFleet.objects.filter(
        enabled=True,
        groups__in=user.groups.all(),
    )
    if fleet is not None:
        fleet_id = getattr(fleet, "pk", fleet)
        if fleet_id is None:
            return False
        exposures = exposures.filter(fleet_id=fleet_id)
    return exposures.exists()


def can_use_restricted_srp(user, fleet=None):
    settings = get_access_settings()
    if settings is None:
        return False
    if not user_has_eligible_state(user, settings):
        return False
    if not user_has_exposed_fleet(user, fleet):
        return False
    return True


def accessible_fleets_for(user):
    """Return exposed built-in fleets that currently accept SRP requests."""
    if not can_use_restricted_srp(user):
        return SrpFleetMain.objects.none()

    return (
        SrpFleetMain.objects.select_related("fleet_commander")
        .filter(
            srp_access_exposure__enabled=True,
            srp_access_exposure__groups__in=user.groups.all(),
            fleet_srp_status="",
        )
        .exclude(fleet_srp_code="")
        .distinct()
        .order_by("-fleet_time", "-pk")
    )
