from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.ldap_attribute_candidates import (
    C2_FIRST_WAVE_REVIEWED_CANDIDATES,
    get_reviewed_ldap_candidate,
    list_reviewed_ldap_candidates,
)
from app.services.ldap_attribute_validation import (
    validate_reviewed_ldap_attribute_request,
)
from app.services.ldap_hab_seniority_candidate import (
    LDAP_HAB_SENIORITY_DORMANT_CANDIDATE,
    get_ldap_hab_seniority_dormant_metadata,
)
from app.services.ldap_hab_seniority_policy import (
    LDAP_HAB_SENIORITY_ATTRIBUTE_NAME,
    LDAP_HAB_SENIORITY_POLICY,
)


class LDAPHabSeniorityCandidateTests(unittest.TestCase):
    def test_candidate_matches_reviewed_contract(self):
        candidate = (
            LDAP_HAB_SENIORITY_DORMANT_CANDIDATE
        )

        self.assertEqual(
            candidate.name,
            LDAP_HAB_SENIORITY_ATTRIBUTE_NAME,
        )
        self.assertEqual(
            candidate.value_type,
            "integer32",
        )
        self.assertEqual(
            candidate.allowed_object_classes,
            frozenset({"user"}),
        )
        self.assertEqual(
            candidate.minimum_length,
            0,
        )
        self.assertEqual(
            candidate.maximum_length,
            0,
        )
        self.assertEqual(
            candidate.minimum_value,
            0,
        )
        self.assertEqual(
            candidate.maximum_value,
            2147483647,
        )
        self.assertTrue(candidate.clearable)
        self.assertFalse(candidate.write_authorized)

    def test_metadata_remains_dormant(self):
        metadata = (
            get_ldap_hab_seniority_dormant_metadata()
        )

        self.assertFalse(
            metadata["public_registry_member"]
        )
        self.assertFalse(
            metadata[
                "validation_available_by_default"
            ]
        )
        self.assertFalse(
            metadata["frontend_exposed"]
        )
        self.assertFalse(
            metadata["job_creation_enabled"]
        )
        self.assertFalse(
            metadata["production_enabled"]
        )
        self.assertFalse(
            metadata["candidate"][
                "write_authorized"
            ]
        )
        self.assertFalse(
            metadata["policy"][
                "public_exposure"
            ]
        )

    def test_public_registry_is_unchanged(self):
        expected = {
            "employeeType",
            "preferredLanguage",
            "personalTitle",
            "middleName",
            "comment",
        }

        self.assertEqual(
            set(
                C2_FIRST_WAVE_REVIEWED_CANDIDATES
            ),
            expected,
        )
        self.assertEqual(
            len(list_reviewed_ldap_candidates()),
            5,
        )
        self.assertIsNone(
            get_reviewed_ldap_candidate(
                LDAP_HAB_SENIORITY_ATTRIBUTE_NAME
            )
        )

    def test_default_validation_rejects_attribute(self):
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
        self.assertEqual(
            decision.errors[0]["code"],
            "unknown_attribute",
        )

    def test_isolated_validation_preserves_integer(self):
        candidate = (
            LDAP_HAB_SENIORITY_DORMANT_CANDIDATE
        )

        with patch(
            "app.services."
            "ldap_attribute_validation."
            "get_reviewed_ldap_candidate",
            return_value=candidate,
        ):
            decision = (
                validate_reviewed_ldap_attribute_request(
                    attribute_name=(
                        candidate.name
                    ),
                    object_class="user",
                    operation="set",
                    value=100,
                )
            )

        self.assertTrue(decision.valid)
        self.assertFalse(decision.write_authorized)
        self.assertEqual(
            decision.normalized_value,
            100,
        )
        self.assertIs(
            type(decision.normalized_value),
            int,
        )
        self.assertEqual(
            decision.value_type,
            "integer32",
        )
        self.assertEqual(
            decision.minimum_value,
            LDAP_HAB_SENIORITY_POLICY.minimum_value,
        )
        self.assertEqual(
            decision.maximum_value,
            LDAP_HAB_SENIORITY_POLICY.maximum_value,
        )

    def test_isolated_validation_enforces_bounds(self):
        candidate = (
            LDAP_HAB_SENIORITY_DORMANT_CANDIDATE
        )

        with patch(
            "app.services."
            "ldap_attribute_validation."
            "get_reviewed_ldap_candidate",
            return_value=candidate,
        ):
            negative = (
                validate_reviewed_ldap_attribute_request(
                    attribute_name=candidate.name,
                    object_class="user",
                    operation="set",
                    value=-1,
                )
            )

            wrong_type = (
                validate_reviewed_ldap_attribute_request(
                    attribute_name=candidate.name,
                    object_class="user",
                    operation="set",
                    value="100",
                )
            )

        self.assertFalse(negative.valid)
        self.assertFalse(wrong_type.valid)
        self.assertFalse(negative.write_authorized)
        self.assertFalse(wrong_type.write_authorized)

        self.assertIn(
            "value_below_minimum",
            {
                error["code"]
                for error in negative.errors
            },
        )

        self.assertIn(
            "invalid_value_type",
            {
                error["code"]
                for error in wrong_type.errors
            },
        )


if __name__ == "__main__":
    unittest.main()
