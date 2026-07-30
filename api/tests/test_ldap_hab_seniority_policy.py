from __future__ import annotations

import unittest

from app.services.ad_admin import ALLOWED_ACTIONS
from app.services.ldap_attribute_candidates import (
    C2_FIRST_WAVE_REVIEWED_CANDIDATES,
    get_reviewed_ldap_candidate,
)
from app.services.ldap_attribute_update import (
    LDAP_ATTRIBUTE_UPDATE_ACTION,
    LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED,
    LDAP_ATTRIBUTE_UPDATE_PRODUCTION_ENABLED,
)
from app.services.ldap_attribute_validation import (
    validate_reviewed_ldap_attribute_request,
)
from app.services.ldap_attribute_value_types import (
    normalize_ldap_typed_value,
)
from app.services.ldap_hab_seniority_policy import (
    LDAP_HAB_SENIORITY_ATTRIBUTE_NAME,
    LDAP_HAB_SENIORITY_POLICY,
    LDAP_HAB_SENIORITY_SCHEMA_FACTS,
)


class LDAPHabSeniorityPolicyTests(unittest.TestCase):
    def test_schema_facts_are_recorded(self):
        self.assertEqual(
            LDAP_HAB_SENIORITY_SCHEMA_FACTS[
                "attribute_syntax"
            ],
            "2.5.5.9",
        )
        self.assertEqual(
            LDAP_HAB_SENIORITY_SCHEMA_FACTS[
                "om_syntax"
            ],
            2,
        )
        self.assertTrue(
            LDAP_HAB_SENIORITY_SCHEMA_FACTS[
                "single_valued"
            ]
        )
        self.assertFalse(
            LDAP_HAB_SENIORITY_SCHEMA_FACTS[
                "system_only"
            ]
        )

    def test_policy_is_integer32_and_user_only(self):
        policy = LDAP_HAB_SENIORITY_POLICY

        self.assertEqual(
            policy.value_type,
            "integer32",
        )
        self.assertEqual(
            policy.allowed_object_classes,
            frozenset({"user"}),
        )
        self.assertEqual(
            policy.minimum_value,
            0,
        )
        self.assertEqual(
            policy.maximum_value,
            2147483647,
        )

    def test_policy_remains_dormant(self):
        policy = LDAP_HAB_SENIORITY_POLICY

        self.assertFalse(policy.public_exposure)
        self.assertFalse(policy.write_authorized)
        self.assertFalse(policy.jobs_enabled)
        self.assertFalse(policy.production_enabled)

    def test_value_contract_applies_policy_bounds(self):
        valid = normalize_ldap_typed_value(
            value_type="integer32",
            value=100,
            minimum_value=(
                LDAP_HAB_SENIORITY_POLICY
                .minimum_value
            ),
            maximum_value=(
                LDAP_HAB_SENIORITY_POLICY
                .maximum_value
            ),
        )

        invalid = normalize_ldap_typed_value(
            value_type="integer32",
            value=-1,
            minimum_value=(
                LDAP_HAB_SENIORITY_POLICY
                .minimum_value
            ),
            maximum_value=(
                LDAP_HAB_SENIORITY_POLICY
                .maximum_value
            ),
        )

        self.assertTrue(valid.valid)
        self.assertEqual(valid.normalized_value, 100)
        self.assertFalse(invalid.valid)

    def test_attribute_is_not_registered_or_authorized(self):
        self.assertNotIn(
            LDAP_HAB_SENIORITY_ATTRIBUTE_NAME,
            C2_FIRST_WAVE_REVIEWED_CANDIDATES,
        )
        self.assertIsNone(
            get_reviewed_ldap_candidate(
                LDAP_HAB_SENIORITY_ATTRIBUTE_NAME
            )
        )

        decision = (
            validate_reviewed_ldap_attribute_request(
                attribute_name=(
                    LDAP_HAB_SENIORITY_ATTRIBUTE_NAME
                ),
                object_class="user",
                operation="set",
                value=100,
            )
        )

        self.assertFalse(decision.valid)
        self.assertFalse(decision.write_authorized)
        self.assertFalse(
            LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED
        )
        self.assertFalse(
            LDAP_ATTRIBUTE_UPDATE_PRODUCTION_ENABLED
        )
        self.assertNotIn(
            LDAP_ATTRIBUTE_UPDATE_ACTION,
            ALLOWED_ACTIONS,
        )


if __name__ == "__main__":
    unittest.main()
