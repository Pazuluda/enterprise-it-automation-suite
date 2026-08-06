from pathlib import Path
import re
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
).read_text(encoding="utf-8")

RDS_FIELDS = (
    "msTSAllowLogon",
    "msTSProfilePath",
    "msTSHomeDirectory",
    "msTSHomeDrive",
    "msTSInitialProgram",
    "msTSWorkDirectory",
)


class ADAdminUserRdsProfileWorkerTests(
    unittest.TestCase
):
    def test_worker_allows_six_rds_fields(self):
        start = SOURCE.index("$AllowedProperties = @(")
        end = SOURCE.index(")", start)
        block = SOURCE[start:end]

        for field in RDS_FIELDS:
            self.assertIn(f'"{field}"', block)

    def test_rds_fields_are_user_only(self):
        start = SOURCE.index("$RdsProperties = @(")
        end = SOURCE.index(
            "$MaximumAttributeLengths",
            start,
        )
        block = SOURCE[start:end]

        for field in RDS_FIELDS:
            self.assertIn(f'"{field}"', block)

        self.assertIn(
            '$PersonObjectClass -ne "user"',
            block,
        )

    def test_allow_logon_supports_clear(self):
        self.assertRegex(
            SOURCE,
            re.compile(
                r'\$Key -eq "msTSAllowLogon"'
                r'[\s\S]*?\$null -eq \$RawValue'
                r'[\s\S]*?\$Clear \+= "msTSAllowLogon"'
                r'[\s\S]*?\$RawValue -isnot \[bool\]'
                r'[\s\S]*?\$Replace\["msTSAllowLogon"\]',
            ),
        )

    def test_text_fields_are_scalar_and_bounded(self):
        self.assertIn(
            "$Key -in $RdsTextProperties",
            SOURCE,
        )
        self.assertIn(
            "$RawValue -isnot [string]",
            SOURCE,
        )
        self.assertIn(
            "$RdsTextValue.Length -gt 32767",
            SOURCE,
        )

    def test_rds_home_drive_is_normalized_and_validated(self):
        self.assertRegex(
            SOURCE,
            re.compile(
                r'\$Key -eq "msTSHomeDrive"'
                r'[\s\S]*?ToUpperInvariant\(\)'
                r'[\s\S]*?\^\[A-Z\]:\$',
            ),
        )

    def test_worker_rereads_six_rds_fields(self):
        for field in RDS_FIELDS:
            self.assertIn(field, SOURCE)

        self.assertRegex(
            SOURCE,
            re.compile(
                r'\$UpdatedObject = Get-ADObject'
                r'[\s\S]*?msTSAllowLogon'
                r'[\s\S]*?msTSProfilePath'
                r'[\s\S]*?msTSWorkDirectory',
            ),
        )

    def test_result_exposes_normalized_fields(self):
        for field in (
            "ms_ts_allow_logon",
            "ms_ts_profile_path",
            "ms_ts_home_directory",
            "ms_ts_home_drive",
            "ms_ts_initial_program",
            "ms_ts_work_directory",
        ):
            self.assertIn(f"{field} =", SOURCE)


if __name__ == "__main__":
    unittest.main()
