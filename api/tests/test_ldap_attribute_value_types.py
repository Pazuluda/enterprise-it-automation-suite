import unittest

from app.services.ldap_attribute_candidates import (
    C2_FIRST_WAVE_REVIEWED_CANDIDATES,
)
from app.services.ldap_attribute_value_types import (
    LDAP_SUPPORTED_VALUE_TYPES,
    normalize_ldap_typed_value,
)


class LDAPAttributeValueTypeTests(unittest.TestCase):
    def error_codes(self, result):
        return {
            item["code"]
            for item in result.errors
        }

    def test_supported_types_are_explicit(self):
        self.assertEqual(
            LDAP_SUPPORTED_VALUE_TYPES,
            {
                "single_text",
                "boolean",
                "integer32",
                "integer64",
            },
        )

    def test_text_is_trimmed(self):
        result = normalize_ldap_typed_value(
            value_type="single_text",
            value=" Interne ",
            minimum_length=1,
            maximum_length=20,
        )

        self.assertTrue(result.valid)
        self.assertEqual(
            result.normalized_value,
            "Interne",
        )

    def test_boolean_is_strict(self):
        valid = normalize_ldap_typed_value(
            value_type="boolean",
            value=True,
        )

        self.assertTrue(valid.valid)
        self.assertIs(
            valid.normalized_value,
            True,
        )

        for invalid_value in (
            "true",
            1,
            None,
        ):
            result = normalize_ldap_typed_value(
                value_type="boolean",
                value=invalid_value,
            )

            self.assertFalse(result.valid)
            self.assertIn(
                "invalid_value_type",
                self.error_codes(result),
            )

    def test_integer32_is_strict(self):
        valid = normalize_ldap_typed_value(
            value_type="integer32",
            value=42,
        )

        self.assertTrue(valid.valid)
        self.assertEqual(
            valid.normalized_value,
            42,
        )

        for invalid_value in (
            "42",
            True,
            None,
        ):
            result = normalize_ldap_typed_value(
                value_type="integer32",
                value=invalid_value,
            )

            self.assertFalse(result.valid)
            self.assertIn(
                "invalid_value_type",
                self.error_codes(result),
            )

    def test_integer32_bounds_are_enforced(self):
        below = normalize_ldap_typed_value(
            value_type="integer32",
            value=-2147483649,
        )

        above = normalize_ldap_typed_value(
            value_type="integer32",
            value=2147483648,
        )

        self.assertIn(
            "value_below_minimum",
            self.error_codes(below),
        )
        self.assertIn(
            "value_above_maximum",
            self.error_codes(above),
        )

    def test_integer64_accepts_large_values(self):
        result = normalize_ldap_typed_value(
            value_type="integer64",
            value=5000000000,
        )

        self.assertTrue(result.valid)
        self.assertEqual(
            result.normalized_value,
            5000000000,
        )

    def test_custom_integer_bounds_are_enforced(self):
        below = normalize_ldap_typed_value(
            value_type="integer32",
            value=-1,
            minimum_value=0,
            maximum_value=100,
        )

        above = normalize_ldap_typed_value(
            value_type="integer32",
            value=101,
            minimum_value=0,
            maximum_value=100,
        )

        self.assertIn(
            "value_below_minimum",
            self.error_codes(below),
        )
        self.assertIn(
            "value_above_maximum",
            self.error_codes(above),
        )

    def test_no_new_candidate_is_exposed(self):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
