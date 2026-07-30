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

        handler_start = cls.source.index(
            (
                "function "
                "Invoke-EitasAdAdminUpdateLdapAttributesSimulation"
            )
        )

        handler_end = cls.source.index(
            "function Invoke-EitasAdAdminJob",
            handler_start,
        )

        cls.handler_source = cls.source[
            handler_start:handler_end
        ]

        start = cls.handler_source.index(
            "$AfterValue = $null"
        )

        cls.preview_source = cls.handler_source[
            start:
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

    def test_hab_attribute_is_allowlisted_for_user(
        self,
    ):
        self.assertIn(
            (
                '"msDS-HABSeniorityIndex" = @(\n'
                '            "user"\n'
                "        )"
            ),
            self.handler_source,
        )

    def test_hab_value_type_is_locked_to_integer32(
        self,
    ):
        self.assertIn(
            (
                '"msDS-HABSeniorityIndex" = '
                '"integer32"'
            ),
            self.handler_source,
        )

        self.assertIn(
            "$ValueType -cne $ExpectedValueType",
            self.handler_source,
        )

    def test_normalization_preserves_value_type(
        self,
    ):
        self.assertIn(
            '"value_type",',
            self.handler_source,
        )

        self.assertIn(
            "value_type = $ValueType",
            self.handler_source,
        )

    def test_typed_values_are_not_globally_cast_to_text(
        self,
    ):
        self.assertNotIn(
            "$Value = ([string]$Value).Trim()",
            self.handler_source,
        )

        self.assertIn(
            'if ($ValueType -eq "single_text")',
            self.handler_source,
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
            self.handler_source,
        )
        self.assertNotIn(
            "Set-ADUser",
            self.handler_source,
        )
        self.assertIn(
            '$Mode.Trim() -ine "Simulation"',
            self.handler_source,
        )
        self.assertIn(
            "$ProductionAuthorized -ne $false",
            self.handler_source,
        )
        self.assertIn(
            "$ExecutionAuthorized -ne $false",
            self.handler_source,
        )

    def test_dedicated_runtime_enabled_and_generic_paths_closed(
        self,
    ):
        self.assertNotIn(
            LDAP_ATTRIBUTE_UPDATE_ACTION,
            ALLOWED_ACTIONS,
        )
        self.assertTrue(
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
