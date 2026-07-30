from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.services.ldap_attribute_update import (
    LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED,
    LDAP_ATTRIBUTE_UPDATE_PRODUCTION_ENABLED,
)
from app.services.ldap_hab_seniority_simulation_persistence import (
    LDAP_HAB_SIMULATION_AD_EXECUTION_ENABLED,
    LDAP_HAB_SIMULATION_PRODUCTION_ENABLED,
    LDAP_HAB_SIMULATION_RUNTIME_JOBS_ENABLED,
    LDAPHabSimulationPersistenceError,
    create_ldap_hab_simulation_job_record,
)


ROOT = Path(__file__).resolve().parents[2]
MAIN_FILE = ROOT / "api/main.py"


class LDAPHabSeniorityRuntimeApiTests(
    unittest.TestCase
):
    def setUp(self):
        self.payload = {
            "action": (
                "simulate_hab_seniority_index"
            ),
            "object_identity": (
                "CN=Test HAB,OU=Users,"
                "OU=EITAS,DC=API,DC=LOCAL"
            ),
            "object_class": "user",
            "attribute_name": (
                "msDS-HABSeniorityIndex"
            ),
            "operation": "set",
            "value": 100,
        }

    def test_dedicated_runtime_is_enabled(self):
        self.assertTrue(
            LDAP_HAB_SIMULATION_RUNTIME_JOBS_ENABLED
        )

    def test_production_and_generic_paths_stay_closed(
        self,
    ):
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

    def test_set_job_persists_integer32(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs_file = (
                Path(directory)
                / "ad-admin-jobs.json"
            )

            response, _ = (
                create_ldap_hab_simulation_job_record(
                    jobs_file,
                    self.payload,
                    "Simulation",
                )
            )

            job = response["job"]
            change = job["payload"]["changes"][0]

            self.assertEqual(
                change["attribute_name"],
                "msDS-HABSeniorityIndex",
            )
            self.assertEqual(
                change["value_type"],
                "integer32",
            )
            self.assertEqual(change["value"], 100)
            self.assertIs(type(change["value"]), int)
            self.assertEqual(job["status"], "pending")
            self.assertFalse(
                job["payload"]["execution_authorized"]
            )

    def test_clear_job_persists_null(self):
        payload = dict(self.payload)
        payload["operation"] = "clear"
        payload["value"] = None

        with tempfile.TemporaryDirectory() as directory:
            jobs_file = (
                Path(directory)
                / "ad-admin-jobs.json"
            )

            response, _ = (
                create_ldap_hab_simulation_job_record(
                    jobs_file,
                    payload,
                    "Simulation",
                )
            )

            change = (
                response["job"]
                ["payload"]["changes"][0]
            )

            self.assertEqual(
                change["operation"],
                "clear",
            )
            self.assertIsNone(change["value"])

    def test_production_is_rejected_without_file(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            jobs_file = (
                Path(directory)
                / "ad-admin-jobs.json"
            )

            with self.assertRaises(
                LDAPHabSimulationPersistenceError
            ):
                create_ldap_hab_simulation_job_record(
                    jobs_file,
                    self.payload,
                    "Production",
                )

            self.assertFalse(jobs_file.exists())

    def test_audit_does_not_contain_raw_value(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs_file = (
                Path(directory)
                / "ad-admin-jobs.json"
            )

            _, audit_event = (
                create_ldap_hab_simulation_job_record(
                    jobs_file,
                    self.payload,
                    "Simulation",
                )
            )

            details = audit_event["details"]

            self.assertFalse(
                details["values_included"]
            )
            self.assertNotIn("value", details)
            self.assertNotIn(
                '"value": 100',
                json.dumps(
                    audit_event,
                    ensure_ascii=False,
                ),
            )

    def test_route_is_dedicated_and_rbac_protected(
        self,
    ):
        source = MAIN_FILE.read_text(
            encoding="utf-8"
        )

        route_marker = (
            '"/api/ad-explorer/ldap/"\n'
            '    "hab-seniority/jobs"'
        )
        function_marker = (
            "def "
            "create_ldap_hab_seniority_"
            "simulation_job_api("
        )

        self.assertIn(route_marker, source)
        self.assertIn(function_marker, source)

        start = source.index(function_marker)

        next_route = source.index(
            "\n\n@app.",
            start,
        )

        function_source = source[
            start:next_route
        ]

        self.assertIn(
            "Depends(AD_ACCESS)",
            function_source,
        )
        self.assertIn(
            "service_create_ldap_hab_"
            "simulation_job_record",
            function_source,
        )
        self.assertIn(
            "AD_ADMIN_JOBS_FILE",
            function_source,
        )
        self.assertIn(
            "write_audit_log",
            function_source,
        )
        self.assertIn(
            "LDAPHabSimulationPersistenceError",
            function_source,
        )


if __name__ == "__main__":
    unittest.main()
