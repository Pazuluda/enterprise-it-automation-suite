import unittest

from fastapi import HTTPException

from app.services.ad_admin import (
    normalize_update_object_properties,
)


class ADAdminUserSecurityOptionsTests(
    unittest.TestCase
):
    def test_snake_case_aliases_are_normalized(self):
        result = normalize_update_object_properties({
            "smartcard_logon_required": True,
            "account_not_delegated": False,
        })

        self.assertEqual(
            result["smartcardLogonRequired"],
            True,
        )

        self.assertEqual(
            result["accountNotDelegated"],
            False,
        )

    def test_camel_case_values_are_preserved(self):
        result = normalize_update_object_properties({
            "smartcardLogonRequired": False,
            "accountNotDelegated": True,
        })

        self.assertEqual(
            result["smartcardLogonRequired"],
            False,
        )

        self.assertEqual(
            result["accountNotDelegated"],
            True,
        )

    def test_smartcard_requires_a_real_boolean(self):
        with self.assertRaises(HTTPException):
            normalize_update_object_properties({
                "smartcard_logon_required": 1,
            })

    def test_not_delegated_requires_a_real_boolean(self):
        with self.assertRaises(HTTPException):
            normalize_update_object_properties({
                "account_not_delegated": "true",
            })


if __name__ == "__main__":
    unittest.main()
