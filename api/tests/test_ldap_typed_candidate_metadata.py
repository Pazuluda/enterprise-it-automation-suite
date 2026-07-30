import unittest
from unittest.mock import patch

from app.services.ldap_attribute_candidates import (
    C2_FIRST_WAVE_REVIEWED_CANDIDATES,
    LDAPReviewedCandidate,
)
from app.services.ldap_attribute_validation import (
    validate_reviewed_ldap_attribute_request,
)


ROLES = frozenset({
    "ADAdmin",
    "UltraAdmin",
})


def integer_candidate():
    return LDAPReviewedCandidate(
        name="futureInteger",
        value_type="integer32",
        allowed_object_classes=frozenset({
            "user",
        }),
        minimum_length=0,
        maximum_length=0,
        clearable=True,
        property_sets=(),
        required_roles=ROLES,
        minimum_value=0,
        maximum_value=100,
    )


class LDAPTypedCandidateMetadataTests(
    unittest.TestCase
):
    def codes(self, decision):
        return {
            item["code"]
            for item in decision.errors
        }

    def test_integer_candidate_serializes_bounds(
        self,
    ):
        payload = integer_candidate().to_dict()

        self.assertEqual(
            payload["minimum_value"],
            0,
        )
        self.assertEqual(
            payload["maximum_value"],
            100,
        )

    def test_text_candidate_output_is_unchanged(
        self,
    ):
        payload = (
            C2_FIRST_WAVE_REVIEWED_CANDIDATES[
                "employeeType"
            ].to_dict()
        )

        self.assertNotIn(
            "minimum_value",
            payload,
        )
        self.assertNotIn(
            "maximum_value",
            payload,
        )

    def test_validator_enforces_bounds(self):
        candidate = integer_candidate()

        with patch(
            "app.services."
            "ldap_attribute_validation."
            "get_reviewed_ldap_candidate",
            return_value=candidate,
        ):
            valid = (
                validate_reviewed_ldap_attribute_request(
                    attribute_name="futureInteger",
                    object_class="user",
                    operation="set",
                    value=42,
                )
            )

            below = (
                validate_reviewed_ldap_attribute_request(
                    attribute_name="futureInteger",
                    object_class="user",
                    operation="set",
                    value=-1,
                )
            )

            above = (
                validate_reviewed_ldap_attribute_request(
                    attribute_name="futureInteger",
                    object_class="user",
                    operation="set",
                    value=101,
                )
            )

        self.assertTrue(valid.valid)
        self.assertEqual(
            valid.normalized_value,
            42,
        )
        self.assertFalse(
            valid.write_authorized
        )
        self.assertIn(
            "value_below_minimum",
            self.codes(below),
        )
        self.assertIn(
            "value_above_maximum",
            self.codes(above),
        )

    def test_public_registry_remains_text_only(
        self,
    ):
        self.assertEqual(
            set(C2_FIRST_WAVE_REVIEWED_CANDIDATES),
            {
                "employeeType",
                "preferredLanguage",
                "personalTitle",
                "middleName",
                "comment",
            },
        )

        self.assertTrue(
            all(
                candidate.value_type
                == "single_text"
                for candidate in (
                    C2_FIRST_WAVE_REVIEWED_CANDIDATES
                    .values()
                )
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
