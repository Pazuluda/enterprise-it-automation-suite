from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdLookup.ps1"
).read_text(encoding="utf-8")


RAW_FIELDS = (
    "wWWHomePage",
    "userWorkstations",
    "logonHours",
    "directReports",
    "profilePath",
    "scriptPath",
    "homeDirectory",
    "homeDrive",
    "homePhone",
    "facsimileTelephoneNumber",
    "pager",
    "ipPhone",
    "postOfficeBox",
    "c",
    "countryCode",
)


NORMALIZED_FIELDS = (
    "www_home_page",
    "user_workstations",
    "logon_hours",
    "logon_hours_utc_offset_minutes",
    "direct_reports",
    "profile_path",
    "script_path",
    "home_directory",
    "home_drive",
    "home_phone",
    "facsimile_telephone_number",
    "pager",
    "ip_phone",
    "post_office_box",
    "post_office_box_count",
    "country_alpha2",
    "country_numeric_code",
)


def get_function_block(
    function_name: str,
    next_function_name: str,
) -> str:
    start = SOURCE.index(
        f"function {function_name}"
    )
    end = SOURCE.index(
        f"function {next_function_name}",
        start,
    )
    return SOURCE[start:end]


class ADLookupUserCompleteProfileWorkerTests(
    unittest.TestCase
):
    def test_converter_exposes_complete_profile(self):
        block = get_function_block(
            "Convert-EitasAdUserItem",
            "Convert-EitasAdGroupItem",
        )

        for field in RAW_FIELDS:
            self.assertIn(field, block)

        for field in NORMALIZED_FIELDS:
            self.assertIn(
                f"{field} =",
                block,
            )

    def test_search_users_requests_complete_profile(self):
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

    def test_get_user_requests_complete_profile(self):
        block = get_function_block(
            "Invoke-EitasAdExplorerGetUser",
            "Invoke-EitasAdExplorerGetGroupMembers",
        )

        for field in RAW_FIELDS:
            self.assertIn(field, block)

    def test_logon_hours_remain_typed_hex(self):
        self.assertIn(
            "function Convert-EitasAdByteArrayToHex",
            SOURCE,
        )

        converter = get_function_block(
            "Convert-EitasAdByteArrayToHex",
            "Convert-EitasAdUserItem",
        )

        self.assertIn(
            '([byte]$_).ToString("X2")',
            converter,
        )

        user_block = get_function_block(
            "Convert-EitasAdUserItem",
            "Convert-EitasAdGroupItem",
        )

        self.assertIn(
            (
                "logon_hours = "
                "Convert-EitasAdByteArrayToHex"
            ),
            user_block,
        )

        self.assertIn(
            "logon_hours_utc_offset_minutes =",
            user_block,
        )

    def test_post_office_box_preserves_count(self):
        block = get_function_block(
            "Convert-EitasAdUserItem",
            "Convert-EitasAdGroupItem",
        )

        self.assertIn(
            "$PostOfficeBoxValues = @(",
            block,
        )

        self.assertIn(
            "post_office_box = $PostOfficeBoxValue",
            block,
        )

        self.assertIn(
            "post_office_box_count =",
            block,
        )

        self.assertIn(
            "$PostOfficeBoxValues.Count",
            block,
        )

    def test_country_numeric_code_is_nullable_integer32(self):
        block = get_function_block(
            "Convert-EitasAdUserItem",
            "Convert-EitasAdGroupItem",
        )

        self.assertIn(
            "country_alpha2 = [string]$User.c",
            block,
        )

        self.assertIn(
            "country_numeric_code =",
            block,
        )

        self.assertIn(
            "-Value $User.countryCode",
            block,
        )

        self.assertIn(
            "Convert-EitasAdNullableInt32",
            block,
        )

    def test_direct_reports_remain_read_only_output(self):
        block = get_function_block(
            "Convert-EitasAdUserItem",
            "Convert-EitasAdGroupItem",
        )

        self.assertIn(
            "direct_reports = @($User.directReports)",
            block,
        )


if __name__ == "__main__":
    unittest.main()
