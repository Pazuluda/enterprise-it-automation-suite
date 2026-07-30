from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from app.services.ldap_attribute_candidates import (
    C2_FIRST_WAVE_REVIEWED_CANDIDATES,
    get_reviewed_ldap_candidate,
)
from app.services.ldap_attribute_update import (
    LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED,
    LDAP_ATTRIBUTE_UPDATE_PRODUCTION_ENABLED,
)
from app.services.ldap_hab_seniority_policy import (
    LDAP_HAB_SENIORITY_ATTRIBUTE_NAME,
)
from app.services.ldap_hab_seniority_simulation_persistence import (
    LDAP_HAB_SIMULATION_AD_EXECUTION_ENABLED,
    LDAP_HAB_SIMULATION_PRODUCTION_ENABLED,
    LDAP_HAB_SIMULATION_RUNTIME_JOBS_ENABLED,
    LDAPHabSimulationPersistenceError,
    create_ldap_hab_simulation_job_record,
)


class LDAPHabSimulationPersistenceTests(
    unittest.TestCase
):
    def payload(
        self,
        *,
        operation="set",
        value=100,
    ):
        return {
            "action": (
                "simulate_hab_seniority_index"
            ),
            "object_identity": (
                "CN=Test,OU=Users,"
                "DC=EXAMPLE,DC=LOCAL"
            ),
            "object_class": "user",
            "attribute_name": (
                "msDS-HABSeniorityIndex"
            ),
            "operation": operation,
            "value": value,
            "created_by": "test-suite",
        }

    def create_path(self, directory):
        return Path(directory) / "jobs.json"

    def read_jobs(self, path):
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    def test_set_job_preserves_integer(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.create_path(temp)

            response, audit = (
                create_ldap_hab_simulation_job_record(
                    path,
                    self.payload(value=125),
                    "Simulation",
                )
            )

            jobs = self.read_jobs(path)
            value = (
                jobs[0]["payload"]
                ["changes"][0]["value"]
            )

            self.assertEqual(value, 125)
            self.assertIs(type(value), int)
            self.assertEqual(
                jobs[0]["status"],
                "pending",
            )
            self.assertEqual(
                jobs[0]["type"],
                "ad_admin",
            )
            self.assertFalse(
                jobs[0]["payload"]
                ["production_authorized"]
            )
            self.assertFalse(
                jobs[0]["payload"]
                ["execution_authorized"]
            )
            self.assertEqual(
                response["job"]["id"],
                audit["request_id"],
            )

    def test_clear_job_persists_null(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.create_path(temp)

            create_ldap_hab_simulation_job_record(
                path,
                self.payload(
                    operation="clear",
                    value=None,
                ),
                "Simulation",
            )

            jobs = self.read_jobs(path)

            self.assertIsNone(
                jobs[0]["payload"]
                ["changes"][0]["value"]
            )

    def test_production_rejection_creates_no_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.create_path(temp)

            with self.assertRaisesRegex(
                LDAPHabSimulationPersistenceError,
                "uniquement en mode Simulation",
            ):
                create_ldap_hab_simulation_job_record(
                    path,
                    self.payload(),
                    "Production",
                )

            self.assertFalse(path.exists())

    def test_invalid_integer_creates_no_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.create_path(temp)

            with self.assertRaisesRegex(
                LDAPHabSimulationPersistenceError,
                "invalid_value_type",
            ):
                create_ldap_hab_simulation_job_record(
                    path,
                    self.payload(value="100"),
                    "Simulation",
                )

            self.assertFalse(path.exists())

    def test_existing_jobs_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.create_path(temp)

            path.write_text(
                json.dumps([
                    {
                        "id": "existing-job",
                        "status": "completed",
                    }
                ]),
                encoding="utf-8",
            )

            create_ldap_hab_simulation_job_record(
                path,
                self.payload(value=200),
                "Simulation",
            )

            jobs = self.read_jobs(path)

            self.assertEqual(len(jobs), 2)
            self.assertEqual(
                jobs[0]["id"],
                "existing-job",
            )

    def test_audit_excludes_raw_value(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.create_path(temp)

            _, audit = (
                create_ldap_hab_simulation_job_record(
                    path,
                    self.payload(value=500),
                    "Simulation",
                )
            )

            details = audit["details"]

            self.assertEqual(
                details["attribute_names"],
                ["msDS-HABSeniorityIndex"],
            )
            self.assertEqual(
                details["change_count"],
                1,
            )
            self.assertFalse(
                details["values_included"]
            )
            self.assertNotIn(
                "value",
                details,
            )
            self.assertNotIn(
                "changes",
                details,
            )

    def test_dedicated_runtime_enabled_and_public_paths_closed(self):
        self.assertTrue(
            LDAP_HAB_SIMULATION_RUNTIME_JOBS_ENABLED
        )
        self.assertFalse(
            LDAP_HAB_SIMULATION_PRODUCTION_ENABLED
        )
        self.assertFalse(
            LDAP_HAB_SIMULATION_AD_EXECUTION_ENABLED
        )
        self.assertFalse(
            LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED
        )
        self.assertFalse(
            LDAP_ATTRIBUTE_UPDATE_PRODUCTION_ENABLED
        )
        self.assertEqual(
            len(
                C2_FIRST_WAVE_REVIEWED_CANDIDATES
            ),
            5,
        )
        self.assertIsNone(
            get_reviewed_ldap_candidate(
                LDAP_HAB_SENIORITY_ATTRIBUTE_NAME
            )
        )


if __name__ == "__main__":
    unittest.main()
