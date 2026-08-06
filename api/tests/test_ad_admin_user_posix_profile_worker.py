from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
).read_text(encoding="utf-8")


class ADAdminUserPosixProfileWorkerTests(
    unittest.TestCase
):
    def test_worker_allows_posix_fields(self):
        start = SOURCE.index("$AllowedProperties = @(")
        end = SOURCE.index(")", start)
        block = SOURCE[start:end]

        for field in (
            "uidNumber",
            "gidNumber",
            "unixHomeDirectory",
            "loginShell",
            "gecos",
        ):
            self.assertIn(f'"{field}"', block)

    def test_posix_fields_are_user_only(self):
        start = SOURCE.index(
            "$AdvancedUserProperties = @("
        )
        end = SOURCE.index(
            "$AdvancedProfileTextProperties = @(",
            start,
        )
        block = SOURCE[start:end]

        for field in (
            "uidNumber",
            "gidNumber",
            "unixHomeDirectory",
            "loginShell",
            "gecos",
        ):
            self.assertIn(f'"{field}"', block)

        self.assertIn(
            '$PersonObjectClass -ne "user"',
            block,
        )

    def test_worker_groups_posix_types(self):
        for field in (
            "unixHomeDirectory",
            "loginShell",
            "gecos",
        ):
            self.assertIn(
                f'"{field}"',
                SOURCE[
                    SOURCE.index(
                        "$AdvancedProfileTextProperties"
                    ):
                    SOURCE.index(
                        "$ProfileProperties = @("
                    )
                ],
            )

        integer_start = SOURCE.index(
            "$PosixIntegerProperties = @("
        )
        integer_end = SOURCE.index(
            ")",
            integer_start,
        )
        integer_block = SOURCE[
            integer_start:integer_end
        ]

        self.assertIn('"uidNumber"', integer_block)
        self.assertIn('"gidNumber"', integer_block)
        self.assertIn("[int]::TryParse", SOURCE)

    def test_worker_uses_schema_limits(self):
        self.assertIn(
            "unixHomeDirectory = 2048",
            SOURCE,
        )
        self.assertIn(
            "loginShell = 1024",
            SOURCE,
        )
        self.assertIn(
            "gecos = 10240",
            SOURCE,
        )

    def test_worker_rereads_and_returns_fields(self):
        for raw_field in (
            "uidNumber",
            "gidNumber",
            "unixHomeDirectory",
            "loginShell",
            "gecos",
        ):
            self.assertIn(raw_field, SOURCE)

        for normalized_field in (
            "uid_number",
            "gid_number",
            "unix_home_directory",
            "login_shell",
            "gecos",
        ):
            self.assertIn(
                f"{normalized_field} =",
                SOURCE,
            )

        self.assertIn(
            "[Convert]::ToInt32",
            SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
