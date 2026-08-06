import json
import tempfile
import unittest
from pathlib import Path

from app.services.ad_admin import (
    ADAdminBadRequest,
    create_ad_admin_job,
)


class ADAdminCreateUserProfileTests(
    unittest.TestCase
):
    def base_payload(self):
        return {
            "action": "create_user",
            "first_name": "Copie",
            "last_name": "Controlee",
            "sam_account_name": "copie.controlee",
            "user_principal_name":
                "copie.controlee@API.LOCAL",
            "target_ou_dn":
                "OU=Users,OU=EITAS,"
                "DC=API,DC=LOCAL",
            "temporary_password":
                "Temp!2026-Copie",
            "description":
                "Compte préparé depuis un profil",
            "enabled": False,
            "force_change_at_logon": True,
            "created_by": "c34-backend-test",
            "mode": "Simulation",
        }

    def create_job(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            jobs_file = (
                Path(directory)
                / "ad-admin-jobs.json"
            )

            response, audit = create_ad_admin_job(
                jobs_file,
                payload,
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
            persisted_job.get("action"),
            "create_user",
        )

        self.assertIsInstance(
            persisted_job.get("payload"),
            dict,
        )

        return (
            response,
            audit,
            persisted_job["payload"],
        )

    def test_profile_fields_are_normalized(self):
        payload = self.base_payload()

        payload.update({
            "Title": "Technicien systèmes",
            "Department": "Infrastructure",
            "Division": "IT",
            "Company": "EITAS",
            "Manager":
                "CN=Responsable IT,"
                "OU=Users,OU=EITAS,"
                "DC=API,DC=LOCAL",
            "physicalDeliveryOfficeName":
                "Bordeaux",
            "officePhone": "0102030405",
            "mobilePhone": "0607080910",
            "streetAddress":
                "1 rue de la République",
            "postalCode": "33000",
            "l": "Bordeaux",
            "st": "Nouvelle-Aquitaine",
        })

        response, audit, worker_payload = (
            self.create_job(payload)
        )

        expected = {
            "title": "Technicien systèmes",
            "department": "Infrastructure",
            "division": "IT",
            "company": "EITAS",
            "manager":
                "CN=Responsable IT,"
                "OU=Users,OU=EITAS,"
                "DC=API,DC=LOCAL",
            "office": "Bordeaux",
            "telephone_number": "0102030405",
            "mobile": "0607080910",
            "street_address":
                "1 rue de la République",
            "postal_code": "33000",
            "city": "Bordeaux",
            "state": "Nouvelle-Aquitaine",
        }

        for key, value in expected.items():
            self.assertEqual(
                worker_payload.get(key),
                value,
            )

        self.assertEqual(
            worker_payload[
                "temporary_password"
            ],
            "Temp!2026-Copie",
        )

        audit_details = audit.get(
            "details",
            {},
        )

        expected_profile_fields = sorted(
            set(expected)
            | {"description"}
        )

        self.assertEqual(
            audit_details.get(
                "profile_fields"
            ),
            expected_profile_fields,
        )

        self.assertTrue(
            set(expected).isdisjoint(
                audit_details
            )
        )

        self.assertNotIn(
            "description",
            audit_details,
        )

        self.assertNotIn(
            "temporary_password",
            audit_details,
        )

        audit_text = json.dumps(
            audit,
            ensure_ascii=False,
        )

        response_text = json.dumps(
            response,
            ensure_ascii=False,
        )

        self.assertNotIn(
            "Temp!2026-Copie",
            audit_text,
        )

        self.assertNotIn(
            "Temp!2026-Copie",
            response_text,
        )

    def test_forbidden_source_fields_are_ignored(self):
        payload = self.base_payload()

        payload.update({
            "member_of": [
                "CN=Admins,OU=Groups,"
                "OU=EITAS,DC=API,DC=LOCAL",
            ],
            "groups": ["Admins"],
            "mail": "source@API.LOCAL",
            "employee_id": "EMP-1",
            "employee_number": "42",
            "password_never_expires": True,
            "cannot_change_password": True,
            "object_guid":
                "00000000-0000-0000-0000-000000000001",
            "sid": "S-1-5-21-1-2-3-1001",
            "hab_seniority_index": 12,
        })

        _response, _audit, worker_payload = (
            self.create_job(payload)
        )

        forbidden = {
            "member_of",
            "groups",
            "mail",
            "employee_id",
            "employee_number",
            "password_never_expires",
            "cannot_change_password",
            "object_guid",
            "sid",
            "hab_seniority_index",
        }

        self.assertTrue(
            forbidden.isdisjoint(
                worker_payload
            )
        )

    def test_control_characters_are_rejected(self):
        payload = self.base_payload()

        payload["title"] = (
            "Technicien\nAdministrateur"
        )

        with self.assertRaises(
            ADAdminBadRequest
        ):
            self.create_job(payload)

    def test_manager_must_be_a_dn(self):
        payload = self.base_payload()
        payload["manager"] = "responsable.it"

        with self.assertRaises(
            ADAdminBadRequest
        ):
            self.create_job(payload)

    def test_non_string_profile_is_rejected(self):
        payload = self.base_payload()

        payload["department"] = [
            "Infrastructure"
        ]

        with self.assertRaises(
            ADAdminBadRequest
        ):
            self.create_job(payload)


if __name__ == "__main__":
    unittest.main()
