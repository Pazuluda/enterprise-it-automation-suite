from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
).read_text(encoding="utf-8")


class ADAdminUserAdvancedProfileWorkerTests(
    unittest.TestCase
):
    def test_worker_allows_advanced_profile_fields(self):
        start = SOURCE.index("$AllowedProperties = @(")
        end = SOURCE.index(")", start)
        block = SOURCE[start:end]

        for field in (
            "personalTitle",
            "initials",
            "preferredLanguage",
            "info",
        ):
            self.assertIn(f'"{field}"', block)

    def test_personal_title_and_language_are_user_only(self):
        start = SOURCE.index(
            "$AdvancedUserProperties = @("
        )
        end = SOURCE.index(
            "$ProfileProperties = @(",
            start,
        )
        block = SOURCE[start:end]

        self.assertIn('"personalTitle"', block)
        self.assertIn('"preferredLanguage"', block)
        self.assertIn(
            '$PersonObjectClass -ne "user"',
            block,
        )

    def test_info_is_allowed_for_users(self):
        start = SOURCE.index("$HasInfoChanges")
        end = SOURCE.index(
            "$HasGroupSpecificChanges",
            start,
        )
        block = SOURCE[start:end]

        self.assertIn('"user"', block)
        self.assertIn('"group"', block)
        self.assertIn('"contact"', block)

    def test_worker_uses_schema_limits(self):
        self.assertIn("personalTitle = 64", SOURCE)
        self.assertIn("initials = 6", SOURCE)
        self.assertIn(
            "preferredLanguage = 32767",
            SOURCE,
        )
        self.assertIn("info = 1024", SOURCE)

    def test_worker_rereads_and_returns_fields(self):
        for raw_field in (
            "personalTitle",
            "initials",
            "preferredLanguage",
            "info",
        ):
            self.assertIn(raw_field, SOURCE)

        for normalized_field in (
            "personal_title",
            "initials",
            "preferred_language",
            "info",
        ):
            self.assertIn(
                f"{normalized_field} =",
                SOURCE,
            )


if __name__ == "__main__":
    unittest.main()
