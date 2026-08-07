from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
).read_text(encoding="utf-8")


def function_body(name: str) -> str:
    marker = f"function {name} {{"
    start = SOURCE.index(marker)
    end = SOURCE.find(
        "\nfunction ",
        start + len(marker),
    )
    return SOURCE[start:] if end < 0 else SOURCE[start:end]


def before_simulation(body: str) -> str:
    marker = 'if ($Mode -ne "Production")'
    assert marker in body
    return body[:body.index(marker)]


class GroupAdvancedPropertiesSimulationTests(
    unittest.TestCase
):
    def test_update_resolves_real_object_before_simulation(self):
        pre = before_simulation(
            function_body(
                "Invoke-EitasAdAdminUpdateObjectProperties"
            )
        )

        self.assertIn(
            "Resolve-EitasAdAdminObject",
            pre,
        )
        self.assertIn(
            "$Object.DistinguishedName",
            pre,
        )

    def test_managed_by_helper_resolves_active_domain_user(self):
        helper = function_body(
            "Resolve-EitasAdAdminManagedByUser"
        )

        self.assertIn("Get-EitasAdDomainDn", helper)
        self.assertIn("Get-ADUser", helper)
        self.assertIn("-Properties Enabled", helper)
        self.assertIn("$User.Enabled", helper)
        self.assertIn("EndsWith(", helper)
        self.assertNotIn("Assert-EitasDnSafe", helper)

    def test_managed_by_is_prevalidated_before_simulation(self):
        pre = before_simulation(
            function_body(
                "Invoke-EitasAdAdminUpdateObjectProperties"
            )
        )

        self.assertIn(
            '$Properties.ContainsKey("managedBy")',
            pre,
        )
        self.assertIn(
            "Resolve-EitasAdAdminManagedByUser",
            pre,
        )
        self.assertIn(
            "organizationalunit",
            pre,
        )
        self.assertIn(
            "managedBy est réservé",
            pre,
         )

    def test_prevalidation_never_writes_ad(self):
        pre = before_simulation(
            function_body(
                "Invoke-EitasAdAdminUpdateObjectProperties"
            )
        )

        for command in (
            "Set-ADGroup",
            "Set-ADObject",
            "Set-ADUser",
            "Set-ADComputer",
            "Set-ADOrganizationalUnit",
        ):
            self.assertNotIn(
                command,
                pre,
                f"{command} found before Simulation return",
            )


if __name__ == "__main__":
    unittest.main()
