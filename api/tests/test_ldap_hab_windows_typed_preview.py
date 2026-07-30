from __future__ import annotations

from pathlib import Path
import unittest

from app.services.ad_admin import (
    ALLOWED_ACTIONS,
)
from app.services.ldap_attribute_update import (
    LDAP_ATTRIBUTE_UPDATE_ACTION,
)
from app.services.ldap_hab_seniority_simulation_persistence import (
    LDAP_HAB_SIMULATION_AD_EXECUTION_ENABLED,
    LDAP_HAB_SIMULATION_PRODUCTION_ENABLED,
    LDAP_HAB_SIMULATION_RUNTIME_JOBS_ENABLED,
)


class LDAPHabWindowsTypedPreviewTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.path = Path(
            "agent-windows/modules/"
            "EitasAdAdmin.ps1"
        )

        cls.source = cls.path.read_text(
            encoding="utf-8-sig"
        )

        start = cls.source.index(
            "$AfterValue = $null"
        )

        end = cls.source.index(
            "function Invoke-EitasAdAdminJob",
            start,
        )

        cls.preview_source = cls.source[
            start:end
        ]

    def test_unconditional_string_conversion_is_removed(
        self,
    ):
        self.assertNotIn(
            "$AfterValue = [string]$Change.value",
            self.preview_source,
        )

    def test_supported_value_types_are_explicit(self):
        for value_type in (
            "single_text",
            "boolean",
            "integer32",
            "integer64",
        ):
            self.assertIn(
                f'"{value_type}"',
                self.preview_source,
            )

        self.assertIn(
            "switch ($ValueType)",
            self.preview_source,
        )

    def test_integer32_remains_numeric(self):
        self.assertIn(
            "[Convert]::ToInt32",
            self.preview_source,
        )
        self.assertIn(
            "$Change.value -is [int32]",
            self.preview_source,
        )
        self.assertIn(
            "$Change.value -is [int64]",
            self.preview_source,
        )

    def test_boolean_remains_boolean(self):
        self.assertIn(
            "$Change.value -isnot [bool]",
            self.preview_source,
        )
        self.assertIn(
            "$AfterValue = [bool]$Change.value",
            self.preview_source,
        )

    def test_preview_exposes_value_type(self):
        self.assertIn(
            "value_type = $ValueType",
            self.preview_source,
        )
        self.assertIn(
            "after = $AfterValue",
            self.preview_source,
        )

    def test_handler_remains_simulation_only(self):
        self.assertIn(
            "simulated = $true",
            self.preview_source,
        )
        self.assertIn(
            "sans écriture",
            self.preview_source,
        )
        self.assertNotIn(
            "Set-ADObject",
            self.preview_source,
        )
        self.assertNotIn(
            "Set-ADUser",
            self.preview_source,
        )

    def test_runtime_and_generic_paths_remain_closed(
        self,
    ):
        self.assertNotIn(
            LDAP_ATTRIBUTE_UPDATE_ACTION,
            ALLOWED_ACTIONS,
        )
        self.assertFalse(
            LDAP_HAB_SIMULATION_RUNTIME_JOBS_ENABLED
        )
        self.assertFalse(
            LDAP_HAB_SIMULATION_PRODUCTION_ENABLED
        )
        self.assertFalse(
            LDAP_HAB_SIMULATION_AD_EXECUTION_ENABLED
        )


if __name__ == "__main__":
    unittest.main()
