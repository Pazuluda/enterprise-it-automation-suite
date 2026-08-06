from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdLookup.ps1"
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


class ADLookupUserRdsProfileWorkerTests(
    unittest.TestCase
):
    def test_user_result_exposes_six_rds_fields(self):
        start = SOURCE.index(
            "function Convert-EitasAdUserItem"
        )

        end = SOURCE.index(
            "function ",
            start + len(
                "function Convert-EitasAdUserItem"
            ),
        )

        block = SOURCE[start:end]

        for field in RDS_FIELDS:
            self.assertIn(field, block)

        for field in NORMALIZED_FIELDS:
            self.assertIn(f"{field} =", block)

    def test_allow_logon_uses_nullable_bool_converter(self):
        self.assertIn(
            (
                "ms_ts_allow_logon = "
                "Convert-EitasAdBoolValue "
                "-Value $User.msTSAllowLogon"
            ),
            SOURCE,
        )

    def test_search_users_requests_six_rds_fields(self):
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

        for field in RDS_FIELDS:
            self.assertIn(field, block)

    def test_get_user_requests_six_rds_fields(self):
        start = SOURCE.index(
            "function Invoke-EitasAdExplorerGetUser"
        )

        end = SOURCE.index(
            "function Invoke-EitasAdExplorerGetGroupMembers",
            start,
        )

        block = SOURCE[start:end]

        for field in RDS_FIELDS:
            self.assertIn(field, block)

    def test_unrelated_rds_fields_remain_hidden(self):
        for forbidden in (
            "msTSRemoteControl",
            "msTSMaxIdleTime",
            "msTSBrokenConnectionAction",
            "msTSReconnectionAction",
            "msTSConnectClientDrives",
            "msTSConnectPrinterDrives",
        ):
            self.assertNotIn(forbidden, SOURCE)


if __name__ == "__main__":
    unittest.main()
