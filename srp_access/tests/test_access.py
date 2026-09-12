from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import TestCase

from allianceauth.authentication.models import State
from allianceauth.srp.models import SrpFleetMain
from allianceauth.tests.auth_utils import AuthUtils

from srp_access.access import can_use_restricted_srp
from srp_access.models import ExposedSrpFleet, SrpAccessSettings


class AccessTests(TestCase):
    def setUp(self):
        self.public_state = State.objects.create(name="Fixture state 101", priority=101, public=True)
        self.private_state = State.objects.create(name="Fixture state 102", priority=102, public=False)
        self.group = Group.objects.create(name="Fixture group 101")
        self.settings = SrpAccessSettings.objects.create(required_group=self.group)
        self.user = User.objects.create_user("restricted-access-user")
        self.user.profile.state = self.public_state
        self.user.profile.save()

    def add_required_group(self):
        AuthUtils.disconnect_signals()
        try:
            self.user.groups.add(self.group)
        finally:
            AuthUtils.connect_signals()
        self.user.refresh_from_db()

    def set_state(self, state):
        AuthUtils.disconnect_signals()
        try:
            profile = self.user.profile
            profile.state = state
            profile.save()
        finally:
            AuthUtils.connect_signals()
        self.user.refresh_from_db()

    def test_anonymous_is_denied(self):
        self.assertFalse(can_use_restricted_srp(AnonymousUser()))

    def test_eligible_state_without_group_is_denied(self):
        self.assertFalse(can_use_restricted_srp(self.user))

    def test_group_without_eligible_state_is_denied(self):
        self.add_required_group()
        self.set_state(self.private_state)
        self.assertFalse(can_use_restricted_srp(self.user))

    def test_eligible_state_and_group_are_allowed(self):
        self.add_required_group()
        self.assertTrue(can_use_restricted_srp(self.user))

    def test_selected_state_mode_uses_relations_not_names(self):
        self.settings.allow_any_public_state = False
        self.settings.save()
        self.settings.selected_states.add(self.private_state)
        self.set_state(self.private_state)
        self.add_required_group()
        self.assertTrue(can_use_restricted_srp(self.user))

    def test_fleet_must_be_exposed(self):
        self.add_required_group()
        fleet = SrpFleetMain.objects.create(fleet_name="Fixture fleet 101", fleet_time="2026-01-01T00:00:00Z")
        self.assertFalse(can_use_restricted_srp(self.user, fleet))
        ExposedSrpFleet.objects.create(fleet=fleet)
        self.assertTrue(can_use_restricted_srp(self.user, fleet))
