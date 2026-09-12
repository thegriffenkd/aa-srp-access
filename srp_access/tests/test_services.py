from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from srp_access.services import (
    KILLMAIL_NOT_AVAILABLE_MESSAGE,
    KILLMAIL_VALIDATION_MESSAGE,
    ZKILLBOARD_TIMEOUT,
    SrpSubmissionError,
    _get_kill_data,
)


class KillmailLookupTests(SimpleTestCase):
    killmail_id = 138385299
    killmail_hash = "a" * 40

    def response(self, payload):
        response = Mock()
        response.json.return_value = payload
        return response

    def valid_payload(self):
        return [
            {
                "killmail_id": self.killmail_id,
                "zkb": {"hash": self.killmail_hash, "totalValue": 1517.64},
            }
        ]

    @patch("srp_access.services.get_killmails_killmail_id_killmail_hash")
    @patch("srp_access.services.requests.get")
    def test_valid_response_returns_esi_victim_data(self, http_get, get_killmail):
        http_get.return_value = self.response(self.valid_payload())
        get_killmail.return_value = SimpleNamespace(
            victim=SimpleNamespace(ship_type_id=601, character_id=2124703334)
        )

        result = _get_kill_data(str(self.killmail_id))

        self.assertEqual(result, (601, 1517.64, 2124703334))
        request_args, request_kwargs = http_get.call_args
        self.assertEqual(
            request_args[0],
            f"https://zkillboard.com/api/killID/{self.killmail_id}/",
        )
        self.assertEqual(request_kwargs["timeout"], ZKILLBOARD_TIMEOUT)
        self.assertIn("aa-srp-access/", request_kwargs["headers"]["User-Agent"])
        self.assertEqual(request_kwargs["headers"]["Accept-Encoding"], "gzip")
        get_killmail.assert_called_once_with(
            killmail_id=self.killmail_id,
            killmail_hash=self.killmail_hash,
        )

    @patch("srp_access.services.requests.get")
    def test_empty_response_gives_retry_later_message_and_log(self, http_get):
        http_get.return_value = self.response([])

        with self.assertLogs("srp_access.services", level="WARNING") as logs:
            with self.assertRaisesMessage(
                SrpSubmissionError, KILLMAIL_NOT_AVAILABLE_MESSAGE
            ):
                _get_kill_data(self.killmail_id)

        self.assertIn(f"killmail_id={self.killmail_id}", logs.output[0])
        self.assertIn("reason=not_available", logs.output[0])

    @patch("srp_access.services.requests.get")
    def test_timeout_is_handled_and_logged(self, http_get):
        http_get.side_effect = requests.Timeout("fixture timeout")

        with self.assertLogs("srp_access.services", level="WARNING") as logs:
            with self.assertRaisesMessage(SrpSubmissionError, KILLMAIL_VALIDATION_MESSAGE):
                _get_kill_data(self.killmail_id)

        self.assertIn("reason=request", logs.output[0])

    @patch("srp_access.services.requests.get")
    def test_non_success_status_is_handled_and_logged(self, http_get):
        response = self.response({"fixture": "body-must-not-be-logged"})
        response.raise_for_status.side_effect = requests.HTTPError(
            response=SimpleNamespace(status_code=503)
        )
        http_get.return_value = response

        with self.assertLogs("srp_access.services", level="WARNING") as logs:
            with self.assertRaisesMessage(SrpSubmissionError, KILLMAIL_VALIDATION_MESSAGE):
                _get_kill_data(self.killmail_id)

        self.assertIn("status=503", logs.output[0])
        self.assertNotIn("body-must-not-be-logged", logs.output[0])

    @patch("srp_access.services.requests.get")
    def test_non_json_response_is_handled_and_logged(self, http_get):
        response = self.response(None)
        response.json.side_effect = ValueError("fixture invalid JSON")
        http_get.return_value = response

        with self.assertLogs("srp_access.services", level="WARNING") as logs:
            with self.assertRaisesMessage(SrpSubmissionError, KILLMAIL_VALIDATION_MESSAGE):
                _get_kill_data(self.killmail_id)

        self.assertIn("reason=non_json", logs.output[0])

    @patch("srp_access.services.requests.get")
    def test_malformed_responses_are_handled_safely(self, http_get):
        malformed_payloads = [
            {},
            [None],
            [{"killmail_id": self.killmail_id}],
            [
                {
                    "killmail_id": self.killmail_id,
                    "zkb": {"hash": "short", "totalValue": 1},
                }
            ],
            [
                {
                    "killmail_id": self.killmail_id + 1,
                    "zkb": {"hash": self.killmail_hash, "totalValue": 1},
                }
            ],
        ]

        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                http_get.return_value = self.response(payload)
                with self.assertLogs("srp_access.services", level="WARNING"):
                    with self.assertRaisesMessage(
                        SrpSubmissionError, KILLMAIL_VALIDATION_MESSAGE
                    ):
                        _get_kill_data(self.killmail_id)

    @patch("srp_access.services.get_killmails_killmail_id_killmail_hash")
    @patch("srp_access.services.requests.get")
    def test_incomplete_esi_response_is_handled_and_logged(
        self, http_get, get_killmail
    ):
        http_get.return_value = self.response(self.valid_payload())
        get_killmail.return_value = None

        with self.assertLogs("srp_access.services", level="WARNING") as logs:
            with self.assertRaisesMessage(SrpSubmissionError, KILLMAIL_VALIDATION_MESSAGE):
                _get_kill_data(self.killmail_id)

        self.assertIn("reason=incomplete", logs.output[0])
