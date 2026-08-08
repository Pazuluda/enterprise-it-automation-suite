from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services.ad_admin import (
    ADAdminBadRequest,
    ALLOWED_ACTIONS,
    create_ad_admin_job,
)


class ContainerBackendTests(unittest.TestCase):
    def create_job(self, payload):
        with tempfile.TemporaryDirectory() as tmp:
            result = create_ad_admin_job(
                Path(tmp) / "jobs.json",
                payload,
            )

        if isinstance(result, tuple):
            response = result[0]
            audit = result[1]
        else:
            response = result
            audit = None

        job = response.get("job", response)
        return job, audit

    def test_create_container_is_allowed(self):
        self.assertIn(
            "create_container",
            ALLOWED_ACTIONS,
        )

    def test_create_container_normalizes_payload(self):
        job, audit = self.create_job({
            "action": "create_container",
            "name": "  C54-Container  ",
            "parent_dn": "OU=EITAS,DC=API,DC=LOCAL",
            "description": "  C5.4 test  ",
            "created_by": "c5.4-test",
        })

        payload = job["payload"]

        self.assertEqual(
            job["action"],
            "create_container",
        )
        self.assertEqual(
            payload["name"],
            "C54-Container",
        )
        self.assertEqual(
            payload["parent_dn"],
            "OU=EITAS,DC=API,DC=LOCAL",
        )
        self.assertEqual(
            payload["description"],
            "C5.4 test",
        )
        self.assertTrue(
            payload["protected_from_accidental_deletion"]
        )

        if audit is not None:
            self.assertEqual(
                audit["details"]["name"],
                "C54-Container",
            )

    def test_aliases_and_false_protection(self):
        job, _ = self.create_job({
            "action": "create_container",
            "containerName": "C54-Alias",
            "targetParentDn": "OU=EITAS,DC=API,DC=LOCAL",
            "protectedFromAccidentalDeletion": False,
            "created_by": "c5.4-test",
        })

        payload = job["payload"]

        self.assertEqual(
            payload["name"],
            "C54-Alias",
        )
        self.assertEqual(
            payload["parent_dn"],
            "OU=EITAS,DC=API,DC=LOCAL",
        )
        self.assertFalse(
            payload["protected_from_accidental_deletion"]
        )

    def test_missing_parent_is_rejected(self):
        with self.assertRaises(ADAdminBadRequest):
            self.create_job({
                "action": "create_container",
                "name": "C54-Container",
                "created_by": "c5.4-test",
            })

    def test_invalid_lengths_are_rejected(self):
        cases = [
            {
                "name": "X" * 65,
                "description": "",
            },
            {
                "name": "C54-Container",
                "description": "X" * 1025,
            },
        ]

        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(
                    ADAdminBadRequest
                ):
                    self.create_job({
                        "action": "create_container",
                        "parent_dn": "OU=EITAS,DC=API,DC=LOCAL",
                        "created_by": "c5.4-test",
                        **case,
                    })


if __name__ == "__main__":
    unittest.main()
