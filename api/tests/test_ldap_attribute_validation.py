import unittest

from app.services.ldap_attribute_validation import (
    LDAP_ATTRIBUTE_VALIDATION_CONTRACT_VERSION,
    LDAP_ATTRIBUTE_VALIDATION_WRITES_ENABLED,
    assert_ldap_attribute_validation_invariants,
    validate_reviewed_ldap_attribute_request,
)


class LDAPAttributeValidationTests(unittest.TestCase):
    def codes(self, decision):
        return {item["code"] for item in decision.errors}

    def test_valid_set_is_normalized_but_never_authorized(self):
        decision = validate_reviewed_ldap_attribute_request(
            attribute_name=" employeetype ",
            object_class=" USER ",
            operation=" SET ",
            value=" Interne ",
        )
        self.assertTrue(decision.valid)
        self.assertFalse(decision.write_authorized)
        self.assertEqual(decision.normalized_attribute_name, "employeeType")
        self.assertEqual(decision.normalized_object_class, "user")
        self.assertEqual(decision.normalized_operation, "set")
        self.assertEqual(decision.normalized_value, "Interne")
        self.assertEqual(
            decision.contract_version,
            LDAP_ATTRIBUTE_VALIDATION_CONTRACT_VERSION,
        )

    def test_valid_clear_is_non_authorizing(self):
        decision = validate_reviewed_ldap_attribute_request(
            attribute_name="comment",
            object_class="contact",
            operation="clear",
        )
        self.assertTrue(decision.valid)
        self.assertFalse(decision.write_authorized)
        self.assertIsNone(decision.normalized_value)

    def test_unknown_attribute_is_rejected(self):
        decision = validate_reviewed_ldap_attribute_request(
            attribute_name="extensionAttribute15",
            object_class="user",
            operation="set",
            value="test",
        )
        self.assertFalse(decision.valid)
        self.assertIn("unknown_attribute", self.codes(decision))

    def test_object_class_scope_is_enforced(self):
        decision = validate_reviewed_ldap_attribute_request(
            attribute_name="employeeType",
            object_class="contact",
            operation="set",
            value="Interne",
        )
        self.assertFalse(decision.valid)
        self.assertIn("unsupported_object_class", self.codes(decision))

    def test_set_requires_nonempty_text(self):
        wrong_type = validate_reviewed_ldap_attribute_request(
            attribute_name="comment",
            object_class="user",
            operation="set",
            value=123,
        )
        empty = validate_reviewed_ldap_attribute_request(
            attribute_name="middleName",
            object_class="user",
            operation="set",
            value="   ",
        )
        self.assertIn("invalid_value_type", self.codes(wrong_type))
        self.assertIn("empty_set_value", self.codes(empty))

    def test_length_and_control_characters_are_enforced(self):
        too_long = validate_reviewed_ldap_attribute_request(
            attribute_name="preferredLanguage",
            object_class="user",
            operation="set",
            value="x" * 65,
        )
        multiline = validate_reviewed_ldap_attribute_request(
            attribute_name="comment",
            object_class="user",
            operation="set",
            value="Ligne 1\nLigne 2",
        )
        self.assertIn("value_too_long", self.codes(too_long))
        self.assertIn("forbidden_control_character", self.codes(multiline))

    def test_clear_rejects_nonempty_value(self):
        decision = validate_reviewed_ldap_attribute_request(
            attribute_name="comment",
            object_class="contact",
            operation="clear",
            value="conserver",
        )
        self.assertFalse(decision.valid)
        self.assertIn("clear_value_must_be_empty", self.codes(decision))

    def test_invalid_operation_is_rejected(self):
        decision = validate_reviewed_ldap_attribute_request(
            attribute_name="comment",
            object_class="user",
            operation="replace",
            value="test",
        )
        self.assertIn("invalid_operation", self.codes(decision))

    def test_serialization_is_explicit_and_non_authorizing(self):
        payload = validate_reviewed_ldap_attribute_request(
            attribute_name="personalTitle",
            object_class="contact",
            operation="set",
            value="Dr",
        ).to_dict()
        self.assertTrue(payload["valid"])
        self.assertFalse(payload["write_authorized"])
        self.assertEqual(payload["required_roles"], ["ADAdmin", "UltraAdmin"])
        self.assertEqual(payload["errors"], [])

    def test_contract_invariants(self):
        self.assertFalse(LDAP_ATTRIBUTE_VALIDATION_WRITES_ENABLED)
        assert_ldap_attribute_validation_invariants()


if __name__ == "__main__":
    unittest.main()
