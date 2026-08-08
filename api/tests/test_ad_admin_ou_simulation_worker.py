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


class OuSimulationContractTests(unittest.TestCase):
    def test_create_ou_resolves_real_parent_before_simulation(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminCreateOu")
        )
        self.assertIn("Import-EitasActiveDirectoryModule", pre)
        self.assertIn("Get-ADObject", pre)
        self.assertIn("$ParentObject.ObjectClass", pre)
        self.assertIn("organizationalUnit", pre)
        self.assertIn("container", pre)

    def test_create_ou_checks_duplicate_before_simulation(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminCreateOu")
        )
        self.assertIn("Test-EitasAdObjectExists", pre)
        self.assertIn("OU déjà existante", pre)

    def test_create_ou_prevalidation_never_writes_ad(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminCreateOu")
        )
        for command in (
            "New-ADOrganizationalUnit",
            "Set-ADOrganizationalUnit",
            "Remove-ADObject",
            "Move-ADObject",
            "Rename-ADObject",
        ):
            self.assertNotIn(command, pre)

    def test_delete_ou_checks_empty_and_protection_before_simulation(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminDeleteObject")
        )
        self.assertIn('$IsOu', pre)
        self.assertIn("-SearchScope OneLevel", pre)
        self.assertIn("Suppression OU refusée", pre)
        self.assertIn("Get-ADOrganizationalUnit", pre)
        self.assertIn("ProtectedFromAccidentalDeletion", pre)

    def test_delete_ou_prevalidation_never_writes_ad(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminDeleteObject")
        )
        for command in (
            "Set-ADOrganizationalUnit",
            "Remove-ADObject",
        ):
            self.assertNotIn(command, pre)

    def test_rename_ou_checks_sibling_conflict_before_simulation(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminRenameObject")
        )
        self.assertIn('$IsOu', pre)
        self.assertIn('$OuConflict', pre)
        self.assertIn("-SearchScope OneLevel", pre)
        self.assertIn("OU déjà existante", pre)

    def test_move_ou_checks_target_collision_before_simulation(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminMoveObject")
         )
        self.assertIn('$MoveConflict', pre)
        self.assertIn("-SearchScope OneLevel", pre)
        self.assertIn("Un objet du même nom existe déjà", pre)

    def test_update_ou_prevalidates_managedby_and_protection(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminUpdateObjectProperties")
        )
        self.assertIn('$Properties.ContainsKey("managedBy")', pre)
        self.assertIn('"organizationalunit"', pre)
        self.assertIn("$ProtectedFromAccidentalDeletion", pre)
        self.assertIn("$HasManagedByChanges", pre)

    def test_update_ou_prevalidation_never_writes_ad(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminUpdateObjectProperties")
         )
        self.assertNotIn("Set-ADOrganizationalUnit", pre)


if __name__ == "__main__":
    unittest.main()
