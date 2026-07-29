from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.services.ad_admin import (
    ALLOWED_ACTIONS,
    create_ldap_attribute_update_simulation_job,
)
from app.services.ldap_attribute_update import (
    LDAP_ATTRIBUTE_UPDATE_ACTION,
    LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED,
    LDAPAttributeUpdateBadRequest,
)


class LDAPAttributeUpdateJobTests(unittest.TestCase):
    @staticmethod
    def request() -> dict:
        return {
            "action": "update_ldap_attributes",
            "object_identity": (
                "CN=Test,OU=Users,OU=EITAS,DC=API,DC=LOCAL"
            ),
            "object_class": "user",
            "changes": [
                {
                    "attribute_name": "employeeType",
                    "operation": "set",
                    "value": "Interne",
                },
                {
                    "attribute_name": "comment",
                    "operation": "clear",
                },
            ],
            "created_by": "unit-test",
        }

    def test_simulation_job_is_persisted_locked(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs_file = Path(directory) / "jobs.json"

            response, audit = (
                create_ldap_attribute_update_simulation_job(
                    jobs_file,
                    self.request(),
                    "Simulation",
                )
            )

            jobs = json.loads(
                jobs_file.read_text(encoding="utf-8")
            )
            job = jobs[0]

            self.assertEqual(len(jobs), 1)
            self.assertEqual(
                job["action"],
                "update_ldap_attributes",
            )
            self.assertEqual(
                job["payload"]["execution_policy"],
                "simulation_only",
            )
            self.assertTrue(
                job["payload"]["simulation_job_authorized"]
            )
            self.assertFalse(
                job["payload"]["production_authorized"]
            )
            self.assertFalse(
                job["payload"]["execution_authorized"]
            )
            self.assertEqual(response["job"]["id"], job["id"])
            self.assertEqual(audit["request_id"], job["id"])

    def test_existing_jobs_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs_file = Path(directory) / "jobs.json"
            jobs_file.write_text(
                json.dumps(
                    [{
                        "id": "existing-job",
                        "status": "completed",
                    }]
                ),
                encoding="utf-8",
            )

            create_ldap_attribute_update_simulation_job(
                jobs_file,
                self.request(),
                "Simulation",
            )

            jobs = json.loads(
                jobs_file.read_text(encoding="utf-8")
            )

            self.assertEqual(len(jobs), 2)
            self.assertEqual(jobs[0]["id"], "existing-job")

    def test_audit_contains_names_but_not_values(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs_file = Path(directory) / "jobs.json"

            _, audit = (
                create_ldap_attribute_update_simulation_job(
                    jobs_file,
                    self.request(),
                    "Simulation",
                )
            )

            audit_text = json.dumps(
                audit,
                ensure_ascii=False,
            )

            self.assertIn("employeeType", audit_text)
            self.assertIn("comment", audit_text)
            self.assertNotIn("Interne", audit_text)
            self.assertNotIn('"changes"', audit_text)

    def test_production_creates_no_file(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs_file = Path(directory) / "jobs.json"

            with self.assertRaises(
                LDAPAttributeUpdateBadRequest
            ):
                create_ldap_attribute_update_simulation_job(
                    jobs_file,
                    self.request(),
                    "Production",
                )

            self.assertFalse(jobs_file.exists())

    def test_global_action_remains_disabled(self):
        self.assertFalse(
            LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED
        )
        self.assertNotIn(
            LDAP_ATTRIBUTE_UPDATE_ACTION,
            ALLOWED_ACTIONS,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)