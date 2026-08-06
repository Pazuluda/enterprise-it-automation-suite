import unittest

from fastapi import HTTPException

from app.services.ad_admin import (
    normalize_update_object_properties,
)


class ADAdminUserAdvancedProfileTests(unittest.TestCase):
    def test_aliases_are_normalized(self):
        result = normalize_update_object_properties({
            "personal_title": " Mme ",
            "initials": " TV ",
            "preferred_language": " fr-FR ",
            "notes": " Note utilisateur ",
        })

        self.assertEqual(result["personalTitle"], "Mme")
        self.assertEqual(result["initials"], "TV")
        self.assertEqual(
            result["preferredLanguage"],
            "fr-FR",
        )
        self.assertEqual(result["info"], "Note utilisateur")

    def test_canonical_fields_support_clear(self):
        result = normalize_update_object_properties({
            "personalTitle": None,
            "initials": "",
            "preferredLanguage": None,
            "info": "",
        })

        self.assertEqual(result["personalTitle"], "")
        self.assertEqual(result["initials"], "")
        self.assertEqual(result["preferredLanguage"], "")
        self.assertEqual(result["info"], "")

    def test_fields_reject_non_string_values(self):
        for field in (
            "personalTitle",
            "initials",
            "preferredLanguage",
            "info",
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
            "personalTitle": "x" * 65,
            "initials": "x" * 7,
            "preferredLanguage": "x" * 32768,
            "info": "x" * 1025,
        }

        for field, value in invalid_values.items():
            with self.subTest(field=field):
                with self.assertRaises(HTTPException):
                    normalize_update_object_properties({
                        field: value,
                    })


if __name__ == "__main__":
    unittest.main()
