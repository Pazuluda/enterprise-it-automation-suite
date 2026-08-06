import unittest

from fastapi import HTTPException
from app.services.ad_admin import (
    normalize_update_object_properties,
)


class ADAdminUserPosixProfileTests(unittest.TestCase):
    def test_aliases_are_normalized(self):
        result = normalize_update_object_properties({
            "uid_number": " 10001 ",
            "gid_number": 10002,
            "unix_home_directory": " /home/test ",
            "login_shell": " /bin/bash ",
            "gecos": " Test User ",
        })

        self.assertEqual(result["uidNumber"], 10001)
        self.assertEqual(result["gidNumber"], 10002)
        self.assertEqual(
            result["unixHomeDirectory"],
            "/home/test",
        )
        self.assertEqual(result["loginShell"], "/bin/bash")
        self.assertEqual(result["gecos"], "Test User")

    def test_fields_support_clear(self):
        result = normalize_update_object_properties({
            "uidNumber": None,
            "gidNumber": "",
            "unixHomeDirectory": None,
            "loginShell": "",
            "gecos": None,
        })

        self.assertIsNone(result["uidNumber"])
        self.assertIsNone(result["gidNumber"])
        self.assertEqual(result["unixHomeDirectory"], "")
        self.assertEqual(result["loginShell"], "")
        self.assertEqual(result["gecos"], "")

    def test_integer32_boundaries_are_preserved(self):
        result = normalize_update_object_properties({
            "uidNumber": -2147483648,
            "gidNumber": "2147483647",
        })

        self.assertEqual(
            result["uidNumber"],
            -2147483648,
        )
        self.assertEqual(
            result["gidNumber"],
            2147483647,
        )

    def test_integer_fields_reject_invalid_values(self):
        invalid_values = (
            True,
            1.5,
            "1.5",
            "abc",
            [],
            {},
            2147483648,
            -2147483649,
        )

        for field in (
            "uidNumber",
            "gidNumber",
        ):
            for invalid in invalid_values:
                with self.subTest(
                    field=field,
                    invalid=invalid,
                ):
                    with self.assertRaises(HTTPException):
                        normalize_update_object_properties({
                            field: invalid,
                        })

    def test_text_fields_reject_non_string_values(self):
        for field in (
            "unixHomeDirectory",
            "loginShell",
            "gecos",
        ):
            for invalid in (
                1,
                True,
                ["value"],
                {"value": "x"},
            ):
                with self.subTest(
                    field=field,
                    invalid=invalid,
                ):
                    with self.assertRaises(HTTPException):
                        normalize_update_object_properties({
                            field: invalid,
                        })

    def test_schema_limits_are_enforced(self):
        invalid_values = {
            "unixHomeDirectory": "x" * 2049,
            "loginShell": "x" * 1025,
            "gecos": "x" * 10241,
        }

        for field, value in invalid_values.items():
            with self.subTest(field=field):
                with self.assertRaises(HTTPException):
                    normalize_update_object_properties({
                        field: value,
                    })


if __name__ == "__main__":
    unittest.main()
