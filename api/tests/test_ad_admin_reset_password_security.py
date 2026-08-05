import json
import tempfile
import unittest
from pathlib import Path

from app.services.ad_admin import (
    ADAdminBadRequest,
    create_ad_admin_job,
)


SENSITIVE_KEYS = {
    "temporary_password",
    "password",
    "new_password",
}


def collect_sensitive_keys(value):
    found = set()

    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()

            if normalized in SENSITIVE_KEYS:
                found.add(normalized)

            found.update(
                collect_sensitive_keys(child)
            )

    elif isinstance(value, list):
        for child in value:
            found.update(
                collect_sensitive_keys(child)
            )

    return found


class ADAdminResetPasswordSecurityTests(
    unittest.TestCase
):
    object_dn = (
        "CN=C32 Reset Test,"
        "OU=Users,OU=EITAS,"
        "DC=API,DC=LOCAL"
    )

    def create_payload(self, **overrides):
        payload = {
            "action": "reset_password",
            "object_dn": self.object_dn,
            "created_by": "c32-security-test",
            "temporary_password": (
                "C32-Redaction-Marker-01!"
            ),
            "force_change_at_logon": False,
            "unlock_after_reset": False,
        }

        payload.update(overrides)
        return payload

    def test_secret_is_persisted_only_for_worker(
        self,
    ):
        redaction_marker = "C32-Redaction-Marker-01!"

        with tempfile.TemporaryDirectory() as directory:
            jobs_file = (
                Path(directory)
                / "ad-admin-jobs.json"
            )

            response, audit_event = (
                create_ad_admin_job(
                    jobs_file,
                    self.create_payload(),
                )
            )

            persisted_jobs = json.loads(
                jobs_file.read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(
            len(persisted_jobs),
            1,
        )

        persisted_job = persisted_jobs[0]

        self.assertEqual(
            persisted_job["payload"][
                "temporary_password"
            ],
            redaction_marker,
        )

        self.assertFalse(
            persisted_job["payload"][
                "force_change_at_logon"
            ]
        )

        self.assertFalse(
            persisted_job["payload"][
                "unlock_after_reset"
            ]
        )

        response_text = json.dumps(
            response,
            ensure_ascii=False,
        )

        audit_text = json.dumps(
            audit_event,
            ensure_ascii=False,
        )

        self.assertNotIn(
            redaction_marker,
            response_text,
        )

        self.assertNotIn(
            redaction_marker,
            audit_text,
        )

        self.assertEqual(
            collect_sensitive_keys(response),
            set(),
        )

        self.assertEqual(
            collect_sensitive_keys(audit_event),
            set(),
        )

        self.assertEqual(
            audit_event["details"][
                "force_change_at_logon"
            ],
            False,
        )

        self.assertEqual(
            audit_event["details"][
                "unlock_after_reset"
            ],
            False,
        )

        self.assertEqual(
            audit_event["request_id"],
            response["job"]["id"],
        )

    def test_default_options_remain_enabled(
        self,
    ):
        redaction_marker = "C32-Default-Redaction-Marker!"

        payload = self.create_payload(
            temporary_password=redaction_marker,
        )

        payload.pop(
            "force_change_at_logon"
        )

        payload.pop(
            "unlock_after_reset"
        )

        with tempfile.TemporaryDirectory() as directory:
            jobs_file = (
                Path(directory)
                / "ad-admin-jobs.json"
            )

            response, audit_event = (
                create_ad_admin_job(
                    jobs_file,
                    payload,
                )
            )

            persisted_job = json.loads(
                jobs_file.read_text(
                    encoding="utf-8"
                )
            )[0]

        self.assertTrue(
            persisted_job["payload"][
                "force_change_at_logon"
            ]
        )

        self.assertTrue(
            persisted_job["payload"][
                "unlock_after_reset"
            ]
        )

        self.assertTrue(
            audit_event["details"][
                "force_change_at_logon"
            ]
        )

        self.assertTrue(
            audit_event["details"][
                "unlock_after_reset"
            ]
        )

        self.assertNotIn(
            redaction_marker,
            json.dumps(
                response,
                ensure_ascii=False,
            ),
        )

    def test_password_aliases_are_normalized_and_hidden(
        self,
    ):
        for alias in (
            "password",
            "new_password",
        ):
            with self.subTest(alias=alias):
                redaction_marker = (
                    f"C32-{alias}-Redaction-Marker!"
                )

                payload = self.create_payload()

                payload.pop(
                    "temporary_password"
                )

                payload[alias] = redaction_marker

                with tempfile.TemporaryDirectory() as directory:
                    jobs_file = (
                        Path(directory)
                        / "ad-admin-jobs.json"
                    )

                    response, audit_event = (
                        create_ad_admin_job(
                            jobs_file,
                            payload,
                        )
                    )

                    persisted_job = json.loads(
                        jobs_file.read_text(
                            encoding="utf-8"
                        )
                    )[0]

                self.assertEqual(
                    persisted_job["payload"][
                        "temporary_password"
                    ],
                    redaction_marker,
                )

                self.assertNotIn(
                    redaction_marker,
                    json.dumps(
                        response,
                        ensure_ascii=False,
                    ),
                )

                self.assertNotIn(
                    redaction_marker,
                    json.dumps(
                        audit_event,
                        ensure_ascii=False,
                    ),
                )

                self.assertEqual(
                    collect_sensitive_keys(
                        response
                    ),
                    set(),
                )

                self.assertEqual(
                    collect_sensitive_keys(
                        audit_event
                    ),
                    set(),
                )

    def test_missing_password_creates_no_job(
        self,
    ):
        payload = self.create_payload()

        payload.pop(
            "temporary_password"
        )

        with tempfile.TemporaryDirectory() as directory:
            jobs_file = (
                Path(directory)
                / "ad-admin-jobs.json"
            )

            with self.assertRaises(
                ADAdminBadRequest
            ):
                create_ad_admin_job(
                    jobs_file,
                    payload,
                )

            self.assertFalse(
                jobs_file.exists()
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
