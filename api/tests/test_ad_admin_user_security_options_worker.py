from pathlib import Path
import re
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
).read_text(
    encoding="utf-8",
)


class ADAdminUserSecurityOptionsWorkerTests(
    unittest.TestCase
):
    def test_worker_allows_both_security_options(self):
        allowed_start = SOURCE.index(
            "$AllowedProperties = @("
        )

        allowed_end = SOURCE.index(
            ")",
            allowed_start,
        )

        allowed_block = SOURCE[
            allowed_start:allowed_end
        ]

        self.assertIn(
            '"smartcardLogonRequired"',
            allowed_block,
        )

        self.assertIn(
            '"accountNotDelegated"',
            allowed_block,
        )

    def test_options_are_restricted_to_users(self):
        start = SOURCE.index(
            "$AccountProperties = @("
        )

        end = SOURCE.index(
            "$HasAccountChanges",
            start,
        )

        block = SOURCE[start:end]

        self.assertIn(
            '"smartcardLogonRequired"',
            block,
        )

        self.assertIn(
            '"accountNotDelegated"',
            block,
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
                r'[\s\S]*?"smartcardLogonRequired"'
                r'[\s\S]*?"accountNotDelegated"'
                r'[\s\S]*?\$RawValue -isnot \[bool\]',
            ),
        )

    def test_set_ad_user_receives_both_flags(self):
        self.assertIn(
            '$SetUserParameters["SmartcardLogonRequired"]',
            SOURCE,
        )

        self.assertIn(
            '$SetUserParameters["AccountNotDelegated"]',
            SOURCE,
        )

    def test_worker_rereads_effective_values(self):
        self.assertRegex(
            SOURCE,
            re.compile(
                r'\$UpdatedUser = Get-ADUser'
                r'[\s\S]*?SmartcardLogonRequired'
                r'[\s\S]*?AccountNotDelegated',
            ),
        )

        self.assertIn(
            "[bool]$UpdatedUser.SmartcardLogonRequired",
            SOURCE,
        )

        self.assertIn(
            "[bool]$UpdatedUser.AccountNotDelegated",
            SOURCE,
        )

    def test_result_exposes_normalized_fields(self):
        self.assertIn(
            "smartcard_logon_required = (",
            SOURCE,
        )

        self.assertIn(
            "account_not_delegated = (",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
