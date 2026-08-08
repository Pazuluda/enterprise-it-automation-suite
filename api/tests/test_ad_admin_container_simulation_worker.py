from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
).read_text(encoding="utf-8")


def function_body(name):
    marker = "function " + name + " {"
    start = SOURCE.index(marker)
    end = SOURCE.find(
        "\nfunction ",
        start + len(marker),
    )

    if end < 0:
        return SOURCE[start:]

    return SOURCE[start:end]


def before_simulation(value):
    marker = "if ($Mode -ne \"Production\")"

    if marker not in value:
        raise AssertionError(
            "Simulation boundary missing"
        )

    return value[:value.index(marker)]


class ContainerWorkerTests(unittest.TestCase):
    def test_create_prevalidates_parent_and_duplicate(self):
        value = before_simulation(
            function_body(
                "Invoke-EitasAdAdminCreateContainer"
            )
        )

        self.assertIn(
            "Import-EitasActiveDirectoryModule",
            value,
        )
        self.assertIn("Get-ADObject", value)
        self.assertIn("organizationalUnit", value)
        self.assertIn("container", value)
        self.assertIn("$ExistingContainer", value)
        self.assertIn("-SearchScope OneLevel", value)

    def test_create_has_no_write_before_simulation(self):
        value = before_simulation(
            function_body(
                "Invoke-EitasAdAdminCreateContainer"
            )
        )

        for command in (
            "New-ADObject",
            "Set-ADObject",
            "Remove-ADObject",
            "Rename-ADObject",
            "Move-ADObject",
        ):
            self.assertNotIn(command, value)

    def test_create_uses_native_container_in_production(self):
        value = function_body(
            "Invoke-EitasAdAdminCreateContainer"
        )

        self.assertIn("New-ADObject @Params", value)
        self.assertIn(
            "Type = \"container\"",
            value,
        )
        self.assertIn(
            "ProtectedFromAccidentalDeletion",
            value,
        )
        self.assertIn("created_container", value)

    def test_create_container_is_dispatched(self):
        value = function_body(
            "Invoke-EitasAdAdminJob"
        )

        self.assertIn(
            "\"create_container\" {",
            value,
        )
        self.assertIn(
            "Invoke-EitasAdAdminCreateContainer",
            value,
        )

    def test_delete_prevalidates_empty_container(self):
        value = before_simulation(
            function_body(
                "Invoke-EitasAdAdminDeleteObject"
            )
        )

        self.assertIn("$IsContainer", value)
        self.assertIn("$ContainerChildren", value)
        self.assertIn(
            "$ContainerEmptyVerified",
            value,
        )
        self.assertIn(
            "$ContainerWasProtected",
            value,
        )
        self.assertIn(
            "ProtectedFromAccidentalDeletion",
            value,
        )
        self.assertNotIn("Remove-ADObject", value)

    def test_delete_write_stays_after_simulation(self):
        value = function_body(
            "Invoke-EitasAdAdminDeleteObject"
        )
        pre = before_simulation(value)

        self.assertNotIn(
            "-ProtectedFromAccidentalDeletion $false",
            pre,
        )
        self.assertIn(
            "container_protection_disabled",
            value,
        )
        self.assertIn("Remove-ADObject", value)

    def test_rename_checks_container_collision(self):
        value = before_simulation(
            function_body(
                "Invoke-EitasAdAdminRenameObject"
            )
        )

        self.assertIn("$IsContainer", value)
        self.assertIn("$ContainerConflict", value)
        self.assertIn(
            "objectClass=container",
            value,
        )
        self.assertIn(
            "-SearchScope OneLevel",
            value,
        )

    def test_move_keeps_generic_container_support(self):
        value = before_simulation(
            function_body(
                "Invoke-EitasAdAdminMoveObject"
            )
        )

        self.assertIn("organizationalUnit", value)
        self.assertIn("container", value)
        self.assertIn("$MoveConflict", value)

    def test_update_supports_container_protection(self):
        value = function_body(
            "Invoke-EitasAdAdminUpdateObjectProperties"
        )

        self.assertGreaterEqual(
            value.count("\"container\""),
            3,
        )
        self.assertIn(
            "ProtectedFromAccidentalDeletion",
            value,
        )


if __name__ == "__main__":
    unittest.main()
