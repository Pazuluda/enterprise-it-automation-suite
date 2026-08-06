from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdLookup.ps1"
).read_text(
    encoding="utf-8",
)


class ADLookupUserSecurityOptionsWorkerTests(
    unittest.TestCase
):
    def test_detailed_lookup_exposes_normalized_values(self):
        self.assertIn(
            (
                "smartcard_logon_required = "
                "Convert-EitasAdBoolValue "
                "-Value $User.SmartcardLogonRequired"
            ),
            SOURCE,
        )

        self.assertIn(
            (
                "account_not_delegated = "
                "Convert-EitasAdBoolValue "
                "-Value $User.AccountNotDelegated"
            ),
            SOURCE,
        )

    def test_get_ad_user_requests_both_properties(self):
        self.assertGreaterEqual(
            SOURCE.count("SmartcardLogonRequired"),
            3,
        )

        self.assertGreaterEqual(
            SOURCE.count("AccountNotDelegated"),
            3,
        )

    def test_ldap_catalog_uses_correct_uac_masks(self):
        self.assertIn(
            (
                "($UserAccountControl "
                "-band 262144) -ne 0"
            ),
            SOURCE,
        )

        self.assertIn(
            (
                "($UserAccountControl "
                "-band 1048576) -ne 0"
            ),
            SOURCE,
        )

    def test_both_lookup_paths_expose_normalized_names(self):
        self.assertEqual(
            SOURCE.count(
                "smartcard_logon_required ="
            ),
            2,
        )

        self.assertEqual(
            SOURCE.count(
                "account_not_delegated ="
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main()
