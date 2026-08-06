from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdSnapshot.ps1"
).read_text(
    encoding="utf-8",
)


class ADSnapshotUserSecurityOptionsWorkerTests(
    unittest.TestCase
):
    def test_snapshot_uses_correct_smartcard_mask(self):
        self.assertEqual(
            SOURCE.count(
                (
                    "($UserAccountControl "
                    "-band 262144) -ne 0"
                )
            ),
            2,
        )

    def test_snapshot_uses_correct_not_delegated_mask(self):
        self.assertEqual(
            SOURCE.count(
                (
                    "($UserAccountControl "
                    "-band 1048576) -ne 0"
                )
            ),
            2,
        )

    def test_snapshot_exposes_both_normalized_fields(self):
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

    def test_security_flags_are_initialized_as_nullable(self):
        self.assertEqual(
            SOURCE.count(
                "$SmartcardLogonRequired = $null"
            ),
            2,
        )

        self.assertEqual(
            SOURCE.count(
                "$AccountNotDelegated = $null"
            ),
            2,
        )

    def test_security_flags_are_user_only(self):
        self.assertGreaterEqual(
            SOURCE.count(
                'if ($Type -eq "user")'
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main()
