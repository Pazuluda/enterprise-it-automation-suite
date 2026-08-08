
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services.ad_admin import (
    ADAdminBadRequest,
    ALLOWED_ACTIONS,
    create_ad_admin_job,
)


class ContactBackendContractTests(unittest.TestCase):
    def create_job(self, payload):
        with tempfile.TemporaryDirectory() as tmp:
            jobs_file = Path(tmp) / "jobs.json"
            return create_ad_admin_job(jobs_file, payload)

    def test_create_contact_is_allowed(self):
        self.assertIn("create_contact", ALLOWED_ACTIONS)

    def test_create_contact_job_normalizes_core_payload(self):
        response, audit = self.create_job({
            "action": "create_contact",
            "name": "  Contact C53  ",
            "target_parent_dn": (
                "OU=Contacts,OU=EITAS,DC=API,DC=LOCAL"
            ),
            "display_name": "  Contact C53 Display  ",
            "first_name": "  Camille  ",
            "last_name": "  Contact  ",
            "mail": "  contact.c53@example.test  ",
            "telephone_number": "  0102030405  ",
            "mobile": "  0607080910  ",
            "company": "  EITAS  ",
            "title": "  Contact externe  ",
            "department": "  Validation  ",
            "description": "  C5.3 contact fixture  ",
            "created_by": "c5.3-test",
        })

        job = response["job"]
        payload = job["payload"]

        self.assertEqual(job["action"], "create_contact")
        self.assertEqual(payload["name"], "Contact C53")
        self.assertEqual(
            payload["target_parent_dn"],
            "OU=Contacts,OU=EITAS,DC=API,DC=LOCAL",
        )
        self.assertEqual(
            payload["display_name"],
            "Contact C53 Display",
        )
        self.assertEqual(payload["first_name"], "Camille")
        self.assertEqual(payload["last_name"], "Contact")
        self.assertEqual(
            payload["mail"],
            "contact.c53@example.test",
        )
        self.assertTrue(
            payload["protected_from_accidental_deletion"]
        )
        self.assertNotIn(
            "contact.c53@example.test",
            repr(audit["details"]),
        )

    def test_create_contact_accepts_parent_and_identity_aliases(self):
        response, _ = self.create_job({
            "action": "create_contact",
            "contactName": "Alias Contact",
            "parentDn": (
                "OU=Contacts,OU=EITAS,DC=API,DC=LOCAL"
            ),
            "displayName": "Alias Display",
            "givenName": "Alias",
            "sn": "Contact",
            "email": "alias@example.test",
            "protectedFromAccidentalDeletion": False,
        })

        payload = response["job"]["payload"]

        self.assertEqual(payload["name"], "Alias Contact")
        self.assertEqual(payload["display_name"], "Alias Display")
        self.assertEqual(payload["first_name"], "Alias")
        self.assertEqual(payload["last_name"], "Contact")
        self.assertEqual(payload["mail"], "alias@example.test")
        self.assertFalse(
            payload["protected_from_accidental_deletion"]
        )

    def test_create_contact_rejects_missing_parent(self):
        with self.assertRaises(ADAdminBadRequest):
            self.create_job({
                "action": "create_contact",
                "name": "Contact C53",
            })

    def test_create_contact_enforces_schema_facing_lengths(self):
        cases = [
            ("name", "X" * 65),
            ("display_name", "X" * 257),
            ("first_name", "X" * 65),
            ("last_name", "X" * 65),
            ("mail", "X" * 257),
            ("telephone_number", "X" * 65),
            ("mobile", "X" * 65),
            ("company", "X" * 65),
            ("title", "X" * 65),
            ("department", "X" * 65),
            ("description", "X" * 1025),
        ]

        for field, value in cases:
            with self.subTest(field=field):
                payload = {
                    "action": "create_contact",
                    "name": "Contact C53",
                    "target_parent_dn": (
                        "OU=Contacts,OU=EITAS,"
                        "DC=API,DC=LOCAL"
                    ),
                    field: value,
                }

                if field == "name":
                    payload["name"] = value

                with self.assertRaises(ADAdminBadRequest):
                    self.create_job(payload)


if __name__ == "__main__":
    unittest.main()
