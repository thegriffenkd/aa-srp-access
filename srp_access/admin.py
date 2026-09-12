from django.contrib import admin
from solo.admin import SingletonModelAdmin

from .models import ExposedSrpFleet, SrpAccessSettings


class SrpManagementPermissionMixin:
    management_permission = "auth.srp_management"

    def _can_manage(self, request):
        return request.user.has_perm(self.management_permission)

    def has_module_permission(self, request):
        return self._can_manage(request)

    def has_view_permission(self, request, obj=None):
        return self._can_manage(request)

    def has_add_permission(self, request):
        return self._can_manage(request)

    def has_change_permission(self, request, obj=None):
        return self._can_manage(request)

    def has_delete_permission(self, request, obj=None):
        return self._can_manage(request)


@admin.register(SrpAccessSettings)
class SrpAccessSettingsAdmin(SrpManagementPermissionMixin, SingletonModelAdmin):
    filter_horizontal = ("selected_states",)


@admin.register(ExposedSrpFleet)
class ExposedSrpFleetAdmin(SrpManagementPermissionMixin, admin.ModelAdmin):
    list_display = ("fleet", "enabled")
    list_filter = ("enabled", "groups")
    list_select_related = ("fleet",)
    filter_horizontal = ("groups",)
    search_fields = (
        "fleet__fleet_name",
        "fleet__fleet_srp_code",
        "groups__name",
    )
