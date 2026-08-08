
from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
).read_text(encoding="utf-8")


def function_body(name: str) -> str:
    marker = f"function {name} {{"
    start = SOURCE.index(marker)
    end = SOURCE.find("\nfunction ", start + len(marker))
    return SOURCE[start:] if end < 0 else SOURCE[start:end]


def before_simulation(body: str) -> str:
    marker = 'if ($Mode -ne "Production")'
    assert marker in body
    return body[:body.index(marker)]


class ContactSimulationWorkerTests(unittest.TestCase):
    def test_create_contact_prevalidates_real_parent_and_duplicate(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminCreateContact")
        )

        self.assertIn(
            "Import-EitasActiveDirectoryModule",
            pre,
        )
        self.assertIn("Get-ADObject", pre)
        self.assertIn("$ParentObject.ObjectClass", pre)
        self.assertIn("organizationalUnit", pre)
        self.assertIn("container", pre)
        self.assertIn("Test-EitasAdObjectExists", pre)
        self.assertIn('"contact"', pre)

    def test_create_contact_prevalidation_never_writes(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminCreateContact")
        )

        for command in (
            "New-ADObject",
            "Set-ADObject",
            "Remove-ADObject",
            "Rename-ADObject",
            "Move-ADObject",
        ):
            self.assertNotIn(command, pre)

    def test_create_contact_production_uses_native_contact_creation(self):
        body = function_body(
            "Invoke-EitasAdAdminCreateContact"
        )

        self.assertIn("New-ADObject @Params", body)
        self.assertIn('Type = "contact"', body)
        self.assertIn(
            "ProtectedFromAccidentalDeletion",
            body,
        )
        self.assertIn("OtherAttributes", body)
        self.assertIn("created_contact", body)

    def test_create_contact_is_dispatched(self):
        body = function_body("Invoke-EitasAdAdminJob")

        self.assertIn('"create_contact" {', body)
        self.assertIn(
            "Invoke-EitasAdAdminCreateContact",
            body,
        )

    def test_contact_rename_checks_sibling_collision_before_simulation(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminRenameObject")
        )

        self.assertIn('$IsContact', pre)
        self.assertIn('$ContactConflict', pre)
        self.assertIn('(objectClass=contact)', pre)
        self.assertIn("-SearchScope OneLevel", pre)

    def test_contact_delete_reads_protection_before_simulation(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminDeleteObject")
        )

        self.assertIn('$IsContact', pre)
        self.assertIn('$ContactWasProtected', pre)
        self.assertIn(
            "ProtectedFromAccidentalDeletion",
            pre,
        )
        self.assertNotIn("Set-ADObject", pre)
        self.assertNotIn("Remove-ADObject", pre)

    def test_contact_delete_disables_protection_only_after_simulation(self):
        body = function_body(
            "Invoke-EitasAdAdminDeleteObject"
        )
        pre = before_simulation(body)

        self.assertNotIn(
            "-ProtectedFromAccidentalDeletion $false",
            pre,
        )
        self.assertIn(
            "-ProtectedFromAccidentalDeletion $false",
            body,
        )
        self.assertIn(
            "contact_protection_disabled",
            body,
        )

    def test_contact_move_uses_generic_destination_collision_prevalidation(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminMoveObject")
        )

        self.assertIn("$MoveConflict", pre)
        self.assertIn("-SearchBase $TargetDn", pre)
        self.assertIn("-SearchScope OneLevel", pre)

    def test_contact_update_path_remains_supported(self):
        pre = before_simulation(
            function_body(
                "Invoke-EitasAdAdminUpdateObjectProperties"
            )
        )

        self.assertIn('"contact"', pre)
        self.assertIn(
            "$ProtectedFromAccidentalDeletion",
            pre,
        )


if __name__ == "__main__":
    unittest.main()
