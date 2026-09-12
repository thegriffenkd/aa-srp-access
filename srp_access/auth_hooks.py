from django.utils.translation import gettext_lazy as _

from allianceauth import hooks
from allianceauth.menu.hooks import MenuItemHook
from allianceauth.services.hooks import UrlHook

from . import urls
from .access import can_use_restricted_srp


class RestrictedSrpMenuItem(MenuItemHook):
    def __init__(self):
        super().__init__(
            _("Restricted SRP"),
            "fa-solid fa-shield-halved",
            "srp_access:fleet_list",
            navactive=["srp_access:"],
        )

    def render(self, request):
        if can_use_restricted_srp(request.user):
            return super().render(request)
        return ""


@hooks.register("menu_item_hook")
def register_menu():
    return RestrictedSrpMenuItem()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "srp_access", r"^srp-access/")
