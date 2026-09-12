from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from allianceauth.authentication.models import CharacterOwnership, State
from allianceauth.eveonline.models import EveCharacter
from allianceauth.srp.models import SrpFleetMain, SrpUserRequest
from allianceauth.tests.auth_utils import AuthUtils

from srp_access.models import ExposedSrpFleet, SrpAccessSettings
from srp_access.services import KILLMAIL_NOT_AVAILABLE_MESSAGE, SrpSubmissionError


class RestrictedViewsTests(TestCase):
    def setUp(self):
        self.state = State.objects.create(name="Fixture state 201", priority=201, public=True)
        self.group = Group.objects.create(name="Fixture group 201")
        SrpAccessSettings.objects.create(required_group=self.group)

        self.user = User.objects.create_user("restricted-view-user")
        self.user.profile.state = self.state
        self.character = EveCharacter.objects.create(
            character_id=90000001,
            character_name="Fixture Pilot 201",
            corporation_id=98000001,
            corporation_name="Fixture Corporation 201",
            corporation_ticker="F201",
        )
        self.user.profile.main_character = self.character
        self.user.profile.save()
        CharacterOwnership.objects.create(
            character=self.character,
            owner_hash="fixture-owner-201",
            user=self.user,
        )

        self.hidden_fleet = SrpFleetMain.objects.create(
            fleet_name="Fixture hidden fleet 201",
            fleet_doctrine="Fixture doctrine A",
            fleet_time=timezone.now(),
            fleet_srp_code="HIDDEN01",
        )
        self.exposed_fleet = SrpFleetMain.objects.create(
            fleet_name="Fixture exposed fleet 202",
            fleet_doctrine="Fixture doctrine B",
            fleet_time=timezone.now(),
            fleet_srp_code="EXPOSE01",
        )
        ExposedSrpFleet.objects.create(fleet=self.exposed_fleet)

    def allow_user(self):
        AuthUtils.disconnect_signals()
        try:
            self.user.groups.add(self.group)
        finally:
            AuthUtils.connect_signals()
        self.user.refresh_from_db()
        self.client.force_login(self.user)

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse("srp_access:fleet_list"))
        self.assertEqual(response.status_code, 302)

    def test_user_without_group_gets_forbidden(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("srp_access:fleet_list"))
        self.assertEqual(response.status_code, 403)

    def test_list_contains_only_exposed_fleet(self):
        self.allow_user()
        response = self.client.get(reverse("srp_access:fleet_list"))
        self.assertContains(response, self.exposed_fleet.fleet_name)
        self.assertNotContains(response, self.hidden_fleet.fleet_name)

    def test_hidden_fleet_direct_url_is_safe_404(self):
        self.allow_user()
        response = self.client.get(
            reverse("srp_access:fleet_detail", args=[self.hidden_fleet.pk])
        )
        self.assertEqual(response.status_code, 404)

    @patch("srp_access.services.get_universe_types_type_id")
    @patch("srp_access.services._get_kill_data")
    def test_exposed_submission_creates_builtin_request(self, get_kill_data, get_type):
        self.allow_user()
        get_kill_data.return_value = (12345, 123456789, self.character.character_id)
        get_type.return_value = SimpleNamespace(name="Fixture Ship 201")

        response = self.client.post(
            reverse("srp_access:request_srp", args=[self.exposed_fleet.pk]),
            {
                "killboard_link": "https://zkillboard.com/kill/123456789/",
                "additional_info": "Fixture details",
            },
        )

        self.assertRedirects(response, reverse("srp_access:fleet_list"))
        request = SrpUserRequest.objects.get()
        self.assertEqual(request.srp_fleet_main, self.exposed_fleet)
        self.assertEqual(request.character, self.character)
        self.assertEqual(request.srp_status, "Pending")

    def test_hidden_submission_is_denied_without_creating_request(self):
        self.allow_user()
        response = self.client.post(
            reverse("srp_access:request_srp", args=[self.hidden_fleet.pk]),
            {"killboard_link": "https://zkillboard.com/kill/987654321/"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(SrpUserRequest.objects.exists())

    @patch("srp_access.services._get_kill_data")
    def test_unavailable_killmail_shows_retry_later_message(self, get_kill_data):
        self.allow_user()
        get_kill_data.side_effect = SrpSubmissionError(
            KILLMAIL_NOT_AVAILABLE_MESSAGE
        )

        response = self.client.post(
            reverse("srp_access:request_srp", args=[self.exposed_fleet.pk]),
            {"killboard_link": "https://zkillboard.com/kill/138385299/"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wait at least five minutes")
        self.assertFalse(SrpUserRequest.objects.exists())

    def test_builtin_srp_flow_remains_available(self):
        AuthUtils.add_permission_to_user_by_name("srp.access_srp", self.user)
        self.client.force_login(self.user)
        response = self.client.get(reverse("srp:management"))
        self.assertEqual(response.status_code, 200)

    @patch("srp_access.services.get_universe_types_type_id")
    @patch("srp_access.services._get_kill_data")
    def test_builtin_admin_can_process_plugin_request(self, get_kill_data, get_type):
        self.allow_user()
        get_kill_data.return_value = (12345, 123456789, self.character.character_id)
        get_type.return_value = SimpleNamespace(name="Fixture Ship 202")
        self.client.post(
            reverse("srp_access:request_srp", args=[self.exposed_fleet.pk]),
            {"killboard_link": "https://zkillboard.com/kill/223456789/"},
        )
        srp_request = SrpUserRequest.objects.get()

        admin_user = User.objects.create_user("fixture-srp-admin")
        AuthUtils.add_main_character(
            admin_user,
            "Fixture Admin 201",
            "90000002",
            corp_id="98000002",
            corp_name="Fixture Corporation 202",
            corp_ticker="F202",
        )
        AuthUtils.add_permission_to_user_by_name("auth.srp_management", admin_user)
        self.client.force_login(admin_user)
        self.client.post(
            reverse("srp:request_approve"),
            {"csrfmiddlewaretoken": "fixture", str(srp_request.pk): "on"},
        )

        srp_request.refresh_from_db()
        self.assertEqual(srp_request.srp_status, "Approved")

    @patch("srp_access.services.get_universe_types_type_id")
    @patch("srp_access.services._get_kill_data")
    def test_duplicate_submission_creates_exactly_one_request(
        self, get_kill_data, get_type
    ):
        self.allow_user()
        get_kill_data.return_value = (12345, 123456789, self.character.character_id)
        get_type.return_value = SimpleNamespace(name="Fixture Ship 203")
        url = reverse("srp_access:request_srp", args=[self.exposed_fleet.pk])
        data = {"killboard_link": "https://zkillboard.com/kill/323456789/"}

        first_response = self.client.post(url, data)
        second_response = self.client.post(url, data)

        self.assertRedirects(first_response, reverse("srp_access:fleet_list"))
        self.assertEqual(second_response.status_code, 200)
        self.assertContains(second_response, "already been submitted")
        self.assertEqual(SrpUserRequest.objects.count(), 1)
        get_kill_data.assert_called_once_with("323456789")
