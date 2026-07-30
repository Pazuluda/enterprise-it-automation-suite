from __future__ import annotations

import unittest

from app.services.ldap_attribute_candidates import (
    C2_FIRST_WAVE_REVIEWED_CANDIDATES,
    get_reviewed_ldap_candidate,
)
from app.services.ldap_hab_seniority_policy import (
    LDAP_HAB_SENIORITY_ATTRIBUTE_NAME,
    LDAP_HAB_SENIORITY_POLICY,
)
from app.services.ldap_hab_seniority_simulation import (
    LDAP_HAB_SIMULATION_ACTION,
    LDAP_HAB_SIMULATION_JOB_CREATION_ENABLED,
    LDAP_HAB_SIMULATION_PRODUCTION_ENABLED,
    LDAPHabSimulationBadRequest,
    normalize_ldap_hab_simulation_request,
)


class LDAPHabSenioritySimulationTests(
    unittest.TestCase
):
    def payload(
        self,
        *,
        operation="set",
        value=100,
        object_class="user",
        attribute_name=(
            "msDS-HABSeniorityIndex"
        ),
    ):
        return {
            "action": LDAP_HAB_SIMULATION_ACTION,
            "object_identity": (
                "CN=Test,OU=Users,"
                "DC=EXAMPLE,DC=LOCAL"
            ),
            "object_class": object_class,
            "attribute_name": attribute_name,
            "operation": operation,
            "value": value,
        }

    def test_set_preserves_integer_value(self):
        request = (
            normalize_ldap_hab_simulation_request(
                self.payload(value=125),
                "Simulation",
            )
        )

        self.assertEqual(request.value, 125)
        self.assertIs(type(request.value), int)
        self.assertEqual(
            request.value_type,
            "integer32",
        )
        self.assertTrue(
            request.simulation_validation_authorized
        )
        self.assertFalse(
            request.simulation_job_authorized
        )
        self.assertFalse(
            request.production_authorized
        )
        self.assertFalse(
            request.execution_authorized
        )

    def test_clear_is_supported_without_value(self):
        request = (
            normalize_ldap_hab_simulation_request(
                self.payload(
                    operation="clear",
                    value=None,
                ),
                "Simulation",
            )
        )

        self.assertEqual(
            request.operation,
            "clear",
        )
        self.assertIsNone(request.value)

    def test_production_mode_is_rejected(self):
        with self.assertRaises(
            LDAPHabSimulationBadRequest
        ):
            normalize_ldap_hab_simulation_request(
                self.payload(),
                "Production",
            )

    def test_negative_value_is_rejected(self):
        with self.assertRaisesRegex(
            LDAPHabSimulationBadRequest,
            "value_below_minimum",
        ):
            normalize_ldap_hab_simulation_request(
                self.payload(value=-1),
                "Simulation",
            )

    def test_string_integer_is_rejected(self):
        with self.assertRaisesRegex(
            LDAPHabSimulationBadRequest,
            "invalid_value_type",
        ):
            normalize_ldap_hab_simulation_request(
                self.payload(value="100"),
                "Simulation",
            )

    def test_non_user_object_is_rejected(self):
        with self.assertRaisesRegex(
            LDAPHabSimulationBadRequest,
            "limité aux utilisateurs",
        ):
            normalize_ldap_hab_simulation_request(
                self.payload(
                    object_class="contact",
                ),
                "Simulation",
            )

    def test_unexpected_attribute_is_rejected(self):
        with self.assertRaisesRegex(
            LDAPHabSimulationBadRequest,
            "Attribut HAB inattendu",
        ):
            normalize_ldap_hab_simulation_request(
                self.payload(
                    attribute_name="employeeType",
                ),
                "Simulation",
            )

    def test_public_registry_and_policy_stay_closed(self):
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

        self.assertFalse(
            LDAP_HAB_SENIORITY_POLICY
            .public_exposure
        )
        self.assertFalse(
            LDAP_HAB_SENIORITY_POLICY
            .write_authorized
        )
        self.assertFalse(
            LDAP_HAB_SIMULATION_JOB_CREATION_ENABLED
        )
        self.assertFalse(
            LDAP_HAB_SIMULATION_PRODUCTION_ENABLED
        )


if __name__ == "__main__":
    unittest.main()
