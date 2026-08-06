from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdSnapshot.ps1"
).read_text(encoding="utf-8")


class ADSnapshotUserAdvancedProfileWorkerTests(
    unittest.TestCase
):
    def test_snapshot_and_catalog_request_fields(self):
        for field in (
            "personalTitle",
            "initials",
            "preferredLanguage",
            "info",
        ):
            self.assertGreaterEqual(
                SOURCE.count(f'"{field}"'),
                2,
                field,
            )

    def test_snapshot_and_catalog_expose_fields(self):
        for field in (
            "personal_title",
            "initials",
            "preferred_language",
            "info",
        ):
            self.assertEqual(
                SOURCE.count(f"{field} ="),
                2,
                field,
            )


if __name__ == "__main__":
    unittest.main()
