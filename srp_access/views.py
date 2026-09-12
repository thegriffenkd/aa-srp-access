from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from .access import accessible_fleets_for, can_use_restricted_srp
from .forms import RestrictedSrpRequestForm
from .services import SrpSubmissionError, create_builtin_srp_request


def _require_base_access(user):
    if not can_use_restricted_srp(user):
        raise PermissionDenied


@login_required
def fleet_list(request):
    _require_base_access(request.user)
    return render(
        request,
        "srp_access/fleet_list.html",
        {"fleets": accessible_fleets_for(request.user)},
    )


@login_required
def fleet_detail(request, fleet_id):
    _require_base_access(request.user)
    fleet = get_object_or_404(accessible_fleets_for(request.user), pk=fleet_id)
    return render(request, "srp_access/fleet_detail.html", {"fleet": fleet})


@login_required
def request_srp(request, fleet_id):
    _require_base_access(request.user)
    fleet = get_object_or_404(accessible_fleets_for(request.user), pk=fleet_id)

    if request.method == "POST":
        form = RestrictedSrpRequestForm(request.POST)
        if form.is_valid():
            try:
                create_builtin_srp_request(
                    user=request.user,
                    fleet=fleet,
                    killboard_link=form.cleaned_data["killboard_link"],
                    additional_info=form.cleaned_data["additional_info"],
                )
            except SrpSubmissionError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, _("Your SRP request was submitted."))
                return redirect("srp_access:fleet_list")
    else:
        form = RestrictedSrpRequestForm()

    return render(
        request,
        "srp_access/request.html",
        {"fleet": fleet, "form": form},
    )
