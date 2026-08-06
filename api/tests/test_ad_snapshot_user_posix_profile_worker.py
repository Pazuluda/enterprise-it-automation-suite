from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdSnapshot.ps1"
).read_text(encoding="utf-8")


class ADSnapshotUserPosixProfileWorkerTests(
    unittest.TestCase
):
    def test_snapshot_has_nullable_integer_converter(self):
        self.assertIn(
            "function Convert-EitasSnapshotNullableInt32",
            SOURCE,
        )
        self.assertIn(
            "[Convert]::ToInt32",
            SOURCE,
        )

    def test_snapshot_and_catalog_request_fields(self):
        for field in (
            "uidNumber",
            "gidNumber",
            "unixHomeDirectory",
            "loginShell",
            "gecos",
        ):
            self.assertGreaterEqual(
                SOURCE.count(f'"{field}"'),
                2,
                field,
            )

    def test_snapshot_and_catalog_expose_fields(self):
        for field in (
            "uid_number",
            "gid_number",
            "unix_home_directory",
            "login_shell",
            "gecos",
        ):
            self.assertEqual(
                SOURCE.count(f"{field} ="),
                2,
                field,
            )

        self.assertGreaterEqual(
            SOURCE.count(
                "Convert-EitasSnapshotNullableInt32"
            ),
            5,
        )


if __name__ == "__main__":
    unittest.main()
