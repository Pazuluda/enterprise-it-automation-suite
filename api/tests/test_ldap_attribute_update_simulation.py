from __future__ import annotations

import unittest

from app.services.ad_admin import ALLOWED_ACTIONS
from app.services.ldap_attribute_update import (
    LDAP_ATTRIBUTE_UPDATE_ACTION,
    LDAP_ATTRIBUTE_UPDATE_EXECUTION_POLICY,
    LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED,
    LDAP_ATTRIBUTE_UPDATE_PRODUCTION_ENABLED,
    LDAPAttributeUpdateBadRequest,
    assert_ldap_attribute_update_simulation_invariants,
    prepare_ldap_attribute_update_simulation_payload,
)


class LDAPAttributeUpdateSimulationTests(unittest.TestCase):
    def request(self):
        return {
            "action": "update_ldap_attributes",
            "object_identity": (
                "CN=Test,OU=Users,OU=EITAS,DC=API,DC=LOCAL"
            ),
            "object_class": "user",
            "changes": [{
                "attribute_name": "employeeType",
                "operation": "set",
                "value": "Interne",
            }],
        }

    def test_simulation_prepares_a_locked_payload(self):
        payload = prepare_ldap_attribute_update_simulation_payload(
            self.request(),
            "Simulation",
        )

        self.assertEqual(
            payload["execution_policy"],
            LDAP_ATTRIBUTE_UPDATE_EXECUTION_POLICY,
        )
        self.assertTrue(payload["simulation_job_authorized"])
        self.assertFalse(payload["production_authorized"])
        self.assertFalse(payload["execution_authorized"])

    def test_simulation_mode_is_normalized(self):
        payload = prepare_ldap_attribute_update_simulation_payload(
            self.request(),
            "  SIMULATION  ",
        )

        self.assertTrue(payload["simulation_job_authorized"])

    def test_production_is_rejected(self):
        with self.assertRaises(LDAPAttributeUpdateBadRequest):
            prepare_ldap_attribute_update_simulation_payload(
                self.request(),
                "Production",
            )

    def test_explicit_mode_is_required(self):
        for mode in (None, "", "inconnu"):
            with self.subTest(mode=mode):
                with self.assertRaises(LDAPAttributeUpdateBadRequest):
                    prepare_ldap_attribute_update_simulation_payload(
                        self.request(),
                        mode,
                    )

    def test_payload_is_revalidated(self):
        request = self.request()
        request["changes"][0]["attribute_name"] = (
            "extensionAttribute15"
        )

        with self.assertRaises(LDAPAttributeUpdateBadRequest):
            prepare_ldap_attribute_update_simulation_payload(
                request,
                "Simulation",
            )

    def test_global_activation_remains_disabled(self):
        self.assertFalse(LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED)
        self.assertFalse(LDAP_ATTRIBUTE_UPDATE_PRODUCTION_ENABLED)
        self.assertNotIn(
            LDAP_ATTRIBUTE_UPDATE_ACTION,
            ALLOWED_ACTIONS,
        )
        assert_ldap_attribute_update_simulation_invariants()


if __name__ == "__main__":
    unittest.main(verbosity=2)
