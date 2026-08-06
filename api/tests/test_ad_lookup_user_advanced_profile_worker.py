from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdLookup.ps1"
).read_text(encoding="utf-8")


RAW_FIELDS = (
    "personalTitle",
    "Initials",
    "preferredLanguage",
    "info",
)

NORMALIZED_FIELDS = (
    "personal_title",
    "initials",
    "preferred_language",
    "info",
)


class ADLookupUserAdvancedProfileWorkerTests(
    unittest.TestCase
):
    def test_user_result_exposes_fields(self):
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

    def test_search_users_requests_fields(self):
        anchor = SOURCE.index(
            'if ($Action -ne "search_users")'
        )
        start = SOURCE.rfind("function ", 0, anchor)
        end = SOURCE.index(
            "function Get-EitasPendingAdExplorerJobs",
            anchor,
        )
        block = SOURCE[start:end]

        for field in (
            "personalTitle",
            "Initials",
            "preferredLanguage",
            "info",
        ):
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

        for field in (
            "personalTitle",
            "Initials",
            "preferredLanguage",
            "info",
        ):
            self.assertIn(field, block)


if __name__ == "__main__":
    unittest.main()
