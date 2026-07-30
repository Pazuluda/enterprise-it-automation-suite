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


class LDAPTypedValidationMetadataTests(
    unittest.TestCase
):
    def test_integer_decision_exposes_bounds(self):
        with patch(
            "app.services."
            "ldap_attribute_validation."
            "get_reviewed_ldap_candidate",
            return_value=integer_candidate(),
        ):
            decision = (
                validate_reviewed_ldap_attribute_request(
                    attribute_name="futureInteger",
                    object_class="user",
                    operation="set",
                    value=42,
                )
            )

        payload = decision.to_dict()

        self.assertTrue(decision.valid)
        self.assertEqual(
            decision.minimum_value,
            0,
        )
        self.assertEqual(
            decision.maximum_value,
            100,
        )
        self.assertEqual(
            payload["minimum_value"],
            0,
        )
        self.assertEqual(
            payload["maximum_value"],
            100,
        )
        self.assertFalse(
            decision.write_authorized
        )

    def test_text_decision_keeps_old_shape(self):
        decision = (
            validate_reviewed_ldap_attribute_request(
                attribute_name="employeeType",
                object_class="user",
                operation="set",
                value="Interne",
            )
        )

        payload = decision.to_dict()

        self.assertTrue(decision.valid)
        self.assertIsNone(
            decision.minimum_value
        )
        self.assertIsNone(
            decision.maximum_value
        )
        self.assertNotIn(
            "minimum_value",
            payload,
        )
        self.assertNotIn(
            "maximum_value",
            payload,
        )

    def test_registry_remains_dormant(self):
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
