import re
import unittest
from pathlib import Path


WORKER_PATH = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
)


class ADAdminCreateUserProfileWorkerTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKER_PATH.read_text(
            encoding="utf-8"
        )

        start_marker = (
            "function "
            "Invoke-EitasAdAdminCreateUser {"
        )

        start = cls.source.index(start_marker)

        next_function = cls.source.find(
            "\nfunction ",
            start + len(start_marker),
        )

        if next_function == -1:
            raise AssertionError(
                "Fin de fonction create_user "
                "introuvable."
            )

        cls.function = cls.source[
            start:next_function
        ]

        specs_start = cls.function.index(
            "$CreateUserProfileSpecs = @("
        )

        specs_end = cls.function.index(
            "$CreateUserProfileValues = @{}",
            specs_start,
        )

        cls.specs = cls.function[
            specs_start:specs_end
        ]

    def test_profile_whitelist_is_exact(self):
        expected = {
            "title": "Title",
            "department": "Department",
            "division": "Division",
            "company": "Company",
            "manager": "Manager",
            "office": "Office",
            "telephone_number": "OfficePhone",
            "mobile": "MobilePhone",
            "street_address": "StreetAddress",
            "postal_code": "PostalCode",
            "city": "City",
            "state": "State",
        }

        keys = re.findall(
            r'Key\s*=\s*"([^"]+)"',
            self.specs,
        )

        parameters = re.findall(
            r'Parameter\s*=\s*"([^"]+)"',
            self.specs,
        )

        self.assertEqual(
            len(keys),
            len(parameters),
        )

        self.assertEqual(
            dict(zip(keys, parameters)),
            expected,
        )

    def test_worker_validates_profile_values(self):
        for fragment in [
            "$ProfileValue.ToCharArray()",
            "[int][char]$_ -lt 32",
            "$ProfileValue.Length -gt",
            "$ProfileSpec.MaximumLength",
            "Repair-EitasTextEncoding",
        ]:
            self.assertIn(
                fragment,
                self.function,
            )

    def test_new_ad_user_receives_profile(self):
        self.assertIn(
            "$CreateUserProfileValues.Keys",
            self.function,
        )

        self.assertIn(
            "$NewUserParams[",
            self.function,
        )

        self.assertIn(
            "New-ADUser @NewUserParams",
            self.function,
        )

    def test_results_expose_only_field_names(self):
        self.assertGreaterEqual(
            self.function.count(
                "profile_fields = @("
            ),
            2,
        )

        for raw_assignment in [
            "title = $",
            "department = $",
            "manager = $",
            "mobile = $",
            "street_address = $",
        ]:
            self.assertNotIn(
                raw_assignment,
                self.function,
            )

    def test_forbidden_copy_operations_are_absent(self):
        for forbidden in [
            'Key = "mail"',
            'Key = "employee_id"',
            'Key = "employee_number"',
            'Key = "password_never_expires"',
            'Key = "cannot_change_password"',
            'Key = "hab_seniority_index"',
            "Add-ADGroupMember",
            "$NewUserParams.Mail",
        ]:
            self.assertNotIn(
                forbidden,
                self.specs
                if forbidden.startswith(
                    'Key = "'
                )
                else self.function,
            )


if __name__ == "__main__":
    unittest.main()
