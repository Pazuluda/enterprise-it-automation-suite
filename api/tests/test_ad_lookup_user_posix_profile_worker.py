from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdLookup.ps1"
).read_text(encoding="utf-8")

RAW_FIELDS = (
    "uidNumber",
    "gidNumber",
    "unixHomeDirectory",
    "loginShell",
    "gecos",
)

NORMALIZED_FIELDS = (
    "uid_number",
    "gid_number",
    "unix_home_directory",
    "login_shell",
    "gecos",
)


class ADLookupUserPosixProfileWorkerTests(
    unittest.TestCase
):
    def test_user_result_exposes_typed_fields(self):
        start = SOURCE.index(
            "function Convert-EitasAdUserItem"
        )
        end = SOURCE.index(
            "function Convert-EitasAdGroupItem",
            start,
        )
        block = SOURCE[start:end]

        for field in RAW_FIELDS:
            self.assertIn(field, block)

        for field in NORMALIZED_FIELDS:
            self.assertIn(f"{field} =", block)

        self.assertGreaterEqual(
            block.count(
                "Convert-EitasAdNullableInt32"
            ),
            2,
        )

    def test_search_users_requests_fields(self):
        anchor = SOURCE.index(
            'if ($Action -ne "search_users")'
        )
        start = SOURCE.rfind(
            "function ",
            0,
            anchor,
        )
        end = SOURCE.index(
            "function Get-EitasPendingAdExplorerJobs",
            anchor,
        )
        block = SOURCE[start:end]

        for field in RAW_FIELDS:
            self.assertIn(field, block)

    def test_get_user_requests_fields(self):
        start = SOURCE.index(
            "function Invoke-EitasAdExplorerGetUser"
        )
        end = SOURCE.index(
            "function Invoke-EitasAdExplorerGetGroupMembers",
            start,
        )
        block = SOURCE[start:end]

        for field in RAW_FIELDS:
            self.assertIn(field, block)


if __name__ == "__main__":
    unittest.main()
