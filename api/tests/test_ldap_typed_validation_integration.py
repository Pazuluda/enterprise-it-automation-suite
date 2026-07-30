import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.models import (
    LDAPAttributeUpdateValidationPayload,
    LDAPAttributeValidationPayload,
)
from app.services.ldap_attribute_candidates import (
    C2_FIRST_WAVE_REVIEWED_CANDIDATES,
)
from app.services.ldap_attribute_validation import (
    LDAP_ATTRIBUTE_VALIDATION_CONTRACT_VERSION,
    validate_reviewed_ldap_attribute_request,
)


def typed_candidate(
    name,
    value_type,
):
    return SimpleNamespace(
        name=name,
        value_type=value_type,
        allowed_object_classes=frozenset({
            "user",
        }),
        minimum_length=0,
        maximum_length=None,
        clearable=True,
        required_roles=frozenset({
            "ADAdmin",
            "UltraAdmin",
        }),
    )


class LDAPTypedValidationIntegrationTests(
    unittest.TestCase
):
    def codes(self, decision):
        return {
            item["code"]
            for item in decision.errors
        }

    def test_existing_text_candidate_is_unchanged(
        self,
    ):
        decision = (
            validate_reviewed_ldap_attribute_request(
                attribute_name="employeeType",
                object_class="user",
                operation="set",
                value=" Interne ",
            )
        )

        self.assertTrue(
            decision.valid
        )

        self.assertEqual(
            decision.normalized_value,
            "Interne",
        )

        self.assertEqual(
            decision.value_type,
            "single_text",
        )

        self.assertFalse(
            decision.write_authorized
        )

    def test_future_boolean_candidate_is_strict(
        self,
    ):
        candidate = typed_candidate(
            "futureBoolean",
            "boolean",
        )

        with patch(
            "app.services."
            "ldap_attribute_validation."
            "get_reviewed_ldap_candidate",
            return_value=candidate,
        ):
            valid = (
                validate_reviewed_ldap_attribute_request(
                    attribute_name="futureBoolean",
                    object_class="user",
                    operation="set",
                    value=True,
                )
            )

            invalid = (
                validate_reviewed_ldap_attribute_request(
                    attribute_name="futureBoolean",
                    object_class="user",
                    operation="set",
                    value="true",
                )
            )

        self.assertTrue(
            valid.valid
        )

        self.assertIs(
            valid.normalized_value,
            True,
        )

        self.assertFalse(
            valid.write_authorized
        )

        self.assertIn(
            "invalid_value_type",
            self.codes(invalid),
        )

    def test_future_integer_candidate_is_strict(
        self,
    ):
        candidate = typed_candidate(
            "futureInteger",
            "integer32",
        )

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

            invalid = (
                validate_reviewed_ldap_attribute_request(
                    attribute_name="futureInteger",
                    object_class="user",
                    operation="set",
                    value=True,
                )
            )

        self.assertTrue(
            valid.valid
        )

        self.assertEqual(
            valid.normalized_value,
            42,
        )

        self.assertIsInstance(
            valid.normalized_value,
            int,
        )

        self.assertFalse(
            valid.write_authorized
        )

        self.assertIn(
            "invalid_value_type",
            self.codes(invalid),
        )

    def test_api_models_preserve_json_types(
        self,
    ):
        boolean_payload = (
            LDAPAttributeValidationPayload(
                attribute_name="futureBoolean",
                object_class="user",
                operation="set",
                value=True,
            )
        )

        integer_payload = (
            LDAPAttributeUpdateValidationPayload(
                action="update_ldap_attributes",
                object_identity=(
                    "CN=Test,OU=Users,OU=EITAS,"
                    "DC=API,DC=LOCAL"
                ),
                object_class="user",
                changes=[{
                    "attribute_name":
                        "futureInteger",
                    "operation": "set",
                    "value": 7,
                }],
            )
        )

        self.assertIs(
            boolean_payload.value,
            True,
        )

        self.assertEqual(
            integer_payload.changes[0].value,
            7,
        )

        self.assertIsInstance(
            integer_payload.changes[0].value,
            int,
        )

    def test_contract_remains_dormant(
        self,
    ):
        self.assertEqual(
            LDAP_ATTRIBUTE_VALIDATION_CONTRACT_VERSION,
            "c2.5c.1",
        )

        self.assertEqual(
            set(
                C2_FIRST_WAVE_REVIEWED_CANDIDATES
            ),
            {
                "employeeType",
                "preferredLanguage",
                "personalTitle",
                "middleName",
                "comment",
            },
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
