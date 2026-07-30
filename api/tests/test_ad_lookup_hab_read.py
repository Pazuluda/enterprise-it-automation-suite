from __future__ import annotations

from pathlib import Path
import unittest


class ADLookupHabReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path(
            "agent-windows/modules/EitasAdLookup.ps1"
        )
        cls.source = cls.path.read_text(
            encoding="utf-8-sig"
        )

        converter_marker = (
            "function Convert-EitasAdNullableInt32"
        )
        converter_start = cls.source.find(
            converter_marker
        )

        if converter_start < 0:
            cls.converter_source = ""
        else:
            converter_end = cls.source.index(
                "function Convert-EitasAdUserItem",
                converter_start,
            )
            cls.converter_source = cls.source[
                converter_start:converter_end
            ]

        user_start = cls.source.index(
            "function Convert-EitasAdUserItem"
        )
        user_end = cls.source.index(
            "function Convert-EitasAdGroupItem",
            user_start,
        )
        cls.user_source = cls.source[
            user_start:user_end
        ]

        get_user_start = cls.source.index(
            "function Invoke-EitasAdExplorerGetUser"
        )
        get_user_end = cls.source.index(
            "function Invoke-EitasAdExplorerGetGroupMembers",
            get_user_start,
        )
        cls.get_user_source = cls.source[
            get_user_start:get_user_end
        ]

        catalog_path = Path(
            "agent-windows/modules/EitasAdSnapshot.ps1"
        )
        catalog_source = catalog_path.read_text(
            encoding="utf-8-sig"
        )
        catalog_start = catalog_source.index(
            "function Convert-EitasDomainCatalogObject"
        )
        catalog_end = catalog_source.index(
            "function New-EitasAdDomainCatalog",
            catalog_start,
        )
        cls.catalog_source = catalog_source[
            catalog_start:catalog_end
        ]

    def test_nullable_integer32_converter_is_explicit(self):
        self.assertIn(
            "function Convert-EitasAdNullableInt32",
            self.source,
        )
        self.assertIn(
            "[Convert]::ToInt32",
            self.converter_source,
        )
        self.assertIn(
            "return $null",
            self.converter_source,
        )
        self.assertIn(
            "Valeur Integer32 Active Directory invalide",
            self.converter_source,
        )

    def test_get_user_requests_hab_attribute(self):
        self.assertIn(
            "msDS-HABSeniorityIndex",
            self.get_user_source,
        )

    def test_get_user_accepts_api_query_identity(self):
        self.assertIn(
            "\"query\"",
            self.get_user_source,
        )

    def test_user_serializer_exposes_nullable_integer32(self):
        self.assertIn(
            "hab_seniority_index =",
            self.user_source,
        )
        self.assertIn(
            "Convert-EitasAdNullableInt32",
            self.user_source,
        )
        self.assertIn(
            "$User.'msDS-HABSeniorityIndex'",
            self.user_source,
        )

    def test_get_user_remains_read_only(self):
        for command in (
            "Set-ADUser",
            "Set-ADObject",
            "Set-ADComputer",
            "Set-ADGroup",
        ):
            self.assertNotIn(
                command,
                self.get_user_source,
            )

    def test_domain_catalog_does_not_expose_hab(self):
        self.assertNotIn(
            "msDS-HABSeniorityIndex",
            self.catalog_source,
        )
        self.assertNotIn(
            "hab_seniority_index",
            self.catalog_source,
        )


if __name__ == "__main__":
    unittest.main()
