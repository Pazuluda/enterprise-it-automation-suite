import unittest

from fastapi import HTTPException

from app.services.ad_admin import (
    normalize_update_object_properties,
)


class ADAdminUserRdsProfileTests(unittest.TestCase):
    def test_snake_case_aliases_are_normalized(self):
        result = normalize_update_object_properties({
            "ms_ts_allow_logon": True,
            "ms_ts_profile_path": r"\\srv\rds\profiles",
            "ms_ts_home_directory": r"\\srv\rds\homes",
            "ms_ts_home_drive": "r:",
            "ms_ts_initial_program": "calc.exe",
            "ms_ts_work_directory": r"C:\RDS",
        })

        self.assertEqual(result["msTSAllowLogon"], True)
        self.assertEqual(
            result["msTSProfilePath"],
            r"\\srv\rds\profiles",
        )
        self.assertEqual(
            result["msTSHomeDirectory"],
            r"\\srv\rds\homes",
        )
        self.assertEqual(result["msTSHomeDrive"], "R:")
        self.assertEqual(
            result["msTSInitialProgram"],
            "calc.exe",
        )
        self.assertEqual(
            result["msTSWorkDirectory"],
            r"C:\RDS",
        )

    def test_camel_case_values_are_preserved(self):
        result = normalize_update_object_properties({
            "msTSAllowLogon": False,
            "msTSProfilePath": " profile ",
        })

        self.assertEqual(result["msTSAllowLogon"], False)
        self.assertEqual(
            result["msTSProfilePath"],
            "profile",
        )

    def test_allow_logon_supports_exact_clear(self):
        result = normalize_update_object_properties({
            "msTSAllowLogon": None,
        })

        self.assertIn("msTSAllowLogon", result)
        self.assertIsNone(result["msTSAllowLogon"])

    def test_allow_logon_rejects_non_boolean_values(self):
        for invalid in (
            1,
            0,
            "true",
            "false",
            "",
            [],
            {},
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(HTTPException):
                    normalize_update_object_properties({
                        "msTSAllowLogon": invalid,
                    })

    def test_rds_text_rejects_collection_values(self):
        for invalid in (
            ["value"],
            {"value": "x"},
            ("value",),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(HTTPException):
                    normalize_update_object_properties({
                        "msTSProfilePath": invalid,
                    })

    def test_rds_text_supports_clear(self):
        result = normalize_update_object_properties({
            "msTSProfilePath": "",
            "msTSHomeDirectory": None,
        })

        self.assertEqual(result["msTSProfilePath"], "")
        self.assertIsNone(result["msTSHomeDirectory"])

    def test_rds_home_drive_is_normalized(self):
        result = normalize_update_object_properties({
            "msTSHomeDrive": " r: ",
        })

        self.assertEqual(result["msTSHomeDrive"], "R:")

    def test_rds_home_drive_rejects_invalid_values(self):
        for invalid in (
            "R",
            "R:\\",
            "RR:",
            "1:",
            "/rds",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(HTTPException):
                    normalize_update_object_properties({
                        "msTSHomeDrive": invalid,
                    })

    def test_rds_text_enforces_schema_limit(self):
        with self.assertRaises(HTTPException):
            normalize_update_object_properties({
                "msTSInitialProgram": "x" * 32768,
            })


if __name__ == "__main__":
    unittest.main()
