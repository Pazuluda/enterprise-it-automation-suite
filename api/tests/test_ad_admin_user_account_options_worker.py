from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

WORKER_PATH = (
    ROOT
    / "agent-windows"
    / "modules"
    / "EitasAdAdmin.ps1"
)

SOURCE = WORKER_PATH.read_text(
    encoding="utf-8"
)


class ADAdminUserAccountOptionsWorkerTests(
    unittest.TestCase
):
    def test_worker_allows_both_properties(self):
        allowed_start = SOURCE.index(
            "$AllowedProperties = @("
        )

        allowed_end = SOURCE.index(
            "\n    )",
            allowed_start,
        )

        allowed_block = SOURCE[
            allowed_start:allowed_end
        ]

        self.assertIn(
            '"passwordNeverExpires"',
            allowed_block,
        )

        self.assertIn(
            '"cannotChangePassword"',
            allowed_block,
        )

    def test_properties_are_user_only(self):
        account_start = SOURCE.index(
            "$AccountProperties = @("
        )

        account_end = SOURCE.index(
            "\n    )",
            account_start,
        )

        account_block = SOURCE[
            account_start:account_end
        ]

        self.assertIn(
            '"passwordNeverExpires"',
            account_block,
        )

        self.assertIn(
            '"cannotChangePassword"',
            account_block,
        )

        self.assertIn(
            '$PersonObjectClass -ne "user"',
            SOURCE,
        )

    def test_worker_requires_real_booleans(self):
        self.assertRegex(
            SOURCE,
            re.compile(
                r'\$Key -in @\('
                r'[\s\S]*?"passwordNeverExpires"'
                r'[\s\S]*?"cannotChangePassword"'
                r'[\s\S]*?\$RawValue -isnot \[bool\]',
            ),
        )

        self.assertIn(
            'doit être un booléen JSON',
            SOURCE,
        )

    def test_false_values_are_not_confused_with_null(self):
        self.assertIn(
            "$PasswordNeverExpiresValue = $null",
            SOURCE,
        )

        self.assertIn(
            "$CannotChangePasswordValue = $null",
            SOURCE,
        )

        self.assertIn(
            "$null -ne $PasswordNeverExpiresValue",
            SOURCE,
        )

        self.assertIn(
            "$null -ne $CannotChangePasswordValue",
            SOURCE,
        )

    def test_set_ad_user_receives_both_options(self):
        self.assertIn(
            '$SetUserParameters["PasswordNeverExpires"]',
            SOURCE,
        )

        self.assertIn(
            '$SetUserParameters["CannotChangePassword"]',
            SOURCE,
        )

        self.assertRegex(
            SOURCE,
            re.compile(
                r'if \(\$SetUserParameters\.Count -gt 2\)'
                r' \{[\s\S]*?Set-ADUser '
                r'@SetUserParameters',
            ),
        )

    def test_worker_rereads_effective_values(self):
        self.assertRegex(
            SOURCE,
            re.compile(
                r'\$UpdatedUser = Get-ADUser'
                r'[\s\S]*?PasswordNeverExpires'
                r'[\s\S]*?CannotChangePassword',
            ),
        )

        self.assertIn(
            "[bool]$UpdatedUser.PasswordNeverExpires",
            SOURCE,
        )

        self.assertIn(
            "[bool]$UpdatedUser.CannotChangePassword",
            SOURCE,
        )

    def test_result_exposes_normalized_fields(self):
        self.assertIn(
            "password_never_expires = (",
            SOURCE,
        )

        self.assertIn(
            "cannot_change_password = (",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
