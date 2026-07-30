from __future__ import annotations

import inspect
import unittest

from app.services.ldap_attribute_candidates import (
    C2_FIRST_WAVE_REVIEWED_CANDIDATES,
    get_reviewed_ldap_candidate,
)
from app.services.ldap_attribute_update import (
    LDAP_ATTRIBUTE_UPDATE_ACTION,
    LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED,
    LDAP_ATTRIBUTE_UPDATE_PRODUCTION_ENABLED,
)
from app.services.ldap_hab_seniority_policy import (
    LDAP_HAB_SENIORITY_ATTRIBUTE_NAME,
)
from app.services.ldap_hab_seniority_simulation_job import (
    LDAP_HAB_SIMULATION_JOB_PERSISTENCE_ENABLED,
    LDAPHabSimulationJobBadRequest,
    get_ldap_hab_simulation_audit_metadata,
    prepare_ldap_hab_simulation_job_envelope,
)


class LDAPHabSimulationJobTests(
    unittest.TestCase
):
    def payload(
        self,
        *,
        operation="set",
        value=100,
        created_by="react-admin",
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
            "created_by": created_by,
        }

    def test_set_envelope_preserves_integer(self):
        envelope = (
            prepare_ldap_hab_simulation_job_envelope(
                self.payload(value=125),
                "Simulation",
            )
        )

        self.assertEqual(
            envelope.action,
            LDAP_ATTRIBUTE_UPDATE_ACTION,
        )
        self.assertEqual(
            envelope.changes[0]["value"],
            125,
        )
        self.assertIs(
            type(
                envelope.changes[0]["value"]
            ),
            int,
        )
        self.assertEqual(
            envelope.changes[0]["value_type"],
            "integer32",
        )
        self.assertTrue(
            envelope.simulation_job_authorized
        )
        self.assertTrue(
            envelope.persistence_authorized
        )
        self.assertFalse(
            envelope.production_authorized
        )
        self.assertFalse(
            envelope.execution_authorized
        )

    def test_clear_envelope_contains_no_value(self):
        envelope = (
            prepare_ldap_hab_simulation_job_envelope(
                self.payload(
                    operation="clear",
                    value=None,
                ),
                "Simulation",
            )
        )

        self.assertEqual(
            envelope.changes[0]["operation"],
            "clear",
        )
        self.assertIsNone(
            envelope.changes[0]["value"]
        )

    def test_production_is_rejected(self):
        with self.assertRaisesRegex(
            LDAPHabSimulationJobBadRequest,
            "uniquement en mode Simulation",
        ):
            prepare_ldap_hab_simulation_job_envelope(
                self.payload(),
                "Production",
            )

    def test_string_integer_is_rejected(self):
        with self.assertRaisesRegex(
            LDAPHabSimulationJobBadRequest,
            "invalid_value_type",
        ):
            prepare_ldap_hab_simulation_job_envelope(
                self.payload(value="100"),
                "Simulation",
            )

    def test_created_by_is_controlled(self):
        envelope = (
            prepare_ldap_hab_simulation_job_envelope(
                self.payload(
                    created_by="  portal-hab  "
                ),
                "Simulation",
            )
        )

        self.assertEqual(
            envelope.created_by,
            "portal-hab",
        )

        with self.assertRaises(
            LDAPHabSimulationJobBadRequest
        ):
            prepare_ldap_hab_simulation_job_envelope(
                self.payload(
                    created_by="portal\nadmin",
                ),
                "Simulation",
            )

    def test_audit_metadata_excludes_values(self):
        envelope = (
            prepare_ldap_hab_simulation_job_envelope(
                self.payload(value=500),
                "Simulation",
            )
        )

        metadata = (
            get_ldap_hab_simulation_audit_metadata(
                envelope
            )
        )

        self.assertEqual(
            metadata["attribute_names"],
            ["msDS-HABSeniorityIndex"],
        )
        self.assertEqual(
            metadata["change_count"],
            1,
        )
        self.assertFalse(
            metadata["values_included"]
        )
        self.assertNotIn(
            "value",
            metadata,
        )
        self.assertNotIn(
            "changes",
            metadata,
        )

    def test_dedicated_persistence_keeps_registry_closed(self):
        self.assertTrue(
            LDAP_HAB_SIMULATION_JOB_PERSISTENCE_ENABLED
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

        source = inspect.getsource(
            prepare_ldap_hab_simulation_job_envelope
        )

        self.assertNotIn(
            "save_json",
            source,
        )
        self.assertNotIn(
            "AD_ADMIN_JOBS_FILE",
            source,
        )
        self.assertNotIn(
            "write_audit_log",
            source,
        )


if __name__ == "__main__":
    unittest.main()
