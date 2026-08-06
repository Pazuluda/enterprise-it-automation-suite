from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdSnapshot.ps1"
).read_text(encoding="utf-8")

RDS_FIELDS = (
    "msTSAllowLogon",
    "msTSProfilePath",
    "msTSHomeDirectory",
    "msTSHomeDrive",
    "msTSInitialProgram",
    "msTSWorkDirectory",
)

NORMALIZED_FIELDS = (
    "ms_ts_allow_logon",
    "ms_ts_profile_path",
    "ms_ts_home_directory",
    "ms_ts_home_drive",
    "ms_ts_initial_program",
    "ms_ts_work_directory",
)


class ADSnapshotUserRdsProfileWorkerTests(
    unittest.TestCase
):
    def test_snapshot_requests_six_rds_fields(self):
        for field in RDS_FIELDS:
            self.assertGreaterEqual(
                SOURCE.count(f'"{field}"'),
                2,
                field,
            )

    def test_snapshot_and_catalog_expose_fields(self):
        for field in NORMALIZED_FIELDS:
            self.assertEqual(
                SOURCE.count(f"{field} ="),
                2,
                field,
            )

    def test_allow_logon_preserves_absent_state(self):
        self.assertEqual(
            SOURCE.count("$MsTsAllowLogon = $null"),
            2,
        )

        self.assertEqual(
            SOURCE.count(
                "$null -ne $Object.msTSAllowLogon"
            ),
            2,
        )

        self.assertEqual(
            SOURCE.count(
                "[bool]$Object.msTSAllowLogon"
            ),
            2,
        )

        self.assertEqual(
            SOURCE.count(
                "ms_ts_allow_logon = $MsTsAllowLogon"
            ),
            2,
        )

    def test_rds_values_are_user_scoped(self):
        self.assertGreaterEqual(
            SOURCE.count('$Type -eq "user"'),
            2,
        )

        self.assertGreaterEqual(
            SOURCE.count(
                "$null -ne $Object.msTSAllowLogon"
            ),
            2,
        )

    def test_unrelated_rds_fields_remain_hidden(self):
        for forbidden in (
            "msTSRemoteControl",
            "msTSMaxIdleTime",
            "msTSMaxConnectionTime",
            "msTSBrokenConnectionAction",
            "msTSReconnectionAction",
            "msTSConnectClientDrives",
            "msTSConnectPrinterDrives",
            "msTSDefaultToMainPrinter",
        ):
            self.assertNotIn(forbidden, SOURCE)


if __name__ == "__main__":
    unittest.main()
