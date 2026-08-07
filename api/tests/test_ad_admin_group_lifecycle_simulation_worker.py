from pathlib import Path
import unittest

SOURCE = Path("agent-windows/modules/EitasAdAdmin.ps1").read_text(encoding="utf-8")

def function_body(name):
    start = SOURCE.index(f"function {name} {{")
    end = SOURCE.find("\nfunction ", start + 1)
    return SOURCE[start:] if end < 0 else SOURCE[start:end]

def before_simulation(body):
    marker = 'if ($Mode -ne "Production")'
    assert marker in body
    return body[:body.index(marker)]

class GroupLifecycleSimulationTests(unittest.TestCase):
    def test_create_group_checks_existing_group_before_simulation(self):
        body = function_body("Invoke-EitasAdAdminCreateGroup")
        pre = before_simulation(body)
        self.assertIn("Test-EitasAdObjectExists", pre)

    def test_delete_resolves_object_and_confirms_real_dn_before_simulation(self):
        body = function_body("Invoke-EitasAdAdminDeleteObject")
        pre = before_simulation(body)
        self.assertIn("Resolve-EitasAdAdminObject", pre)
        self.assertIn("$ObjectDn -ine $ConfirmDn", pre)

    def test_rename_resolves_real_object_before_simulation(self):
        body = function_body("Invoke-EitasAdAdminRenameObject")
        pre = before_simulation(body)
        self.assertIn("Resolve-EitasAdAdminObject", pre)

    def test_move_resolves_source_and_target_before_simulation(self):
        body = function_body("Invoke-EitasAdAdminMoveObject")
        pre = before_simulation(body)
        self.assertIn("Resolve-EitasAdAdminObject", pre)
        self.assertIn("Assert-EitasDnSafe -DistinguishedName $TargetParentDn", pre)
        self.assertIn("Get-ADObject", pre)

    def test_prevalidation_never_writes_ad(self):
        writes = (
            "New-ADGroup",
            "Remove-ADObject",
            "Rename-ADObject",
            "Move-ADObject",
            "Set-ADGroup",
            "Add-ADGroupMember",
            "Remove-ADGroupMember",
        )
        for name in (
            "Invoke-EitasAdAdminCreateGroup",
            "Invoke-EitasAdAdminDeleteObject",
            "Invoke-EitasAdAdminRenameObject",
            "Invoke-EitasAdAdminMoveObject",
        ):
            pre = before_simulation(function_body(name))
            for command in writes:
                self.assertNotIn(command, pre, f"{command} found before Simulation return in {name}")

    def test_move_rejects_non_container_target_before_simulation(self):
        body = function_body("Invoke-EitasAdAdminMoveObject")
        pre = before_simulation(body)
        self.assertIn("$TargetParent.ObjectClass", pre)
        self.assertIn("organizationalUnit", pre)
        self.assertIn("container", pre)


if __name__ == "__main__":
    unittest.main()
