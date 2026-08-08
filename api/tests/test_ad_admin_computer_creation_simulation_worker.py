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


class ComputerCreationSimulationTests(
    unittest.TestCase
):
    def test_create_computer_keeps_scope_guards_before_simulation(self):
        pre = before_simulation(
            function_body(
                "Invoke-EitasAdAdminCreateComputer"
            )
        )

        self.assertIn(
            "OU=COMPUTERS",
            pre,
        )
        self.assertIn(
            "OU=EITAS",
            pre,
        )
        self.assertIn(
            "Assert-EitasDnSafe",
            pre,
        )

    def test_create_computer_resolves_target_ou_before_simulation(self):
        pre = before_simulation(
            function_body(
                "Invoke-EitasAdAdminCreateComputer"
            )
        )

        self.assertIn(
            "Import-EitasActiveDirectoryModule",
            pre,
        )
        self.assertIn(
            "Get-ADOrganizationalUnit",
            pre,
        )

    def test_create_computer_checks_existing_account_before_simulation(self):
        pre = before_simulation(
            function_body(
                "Invoke-EitasAdAdminCreateComputer"
            )
        )

        self.assertIn(
            "Get-ADComputer",
            pre,
        )
        self.assertIn(
            "Ordinateur déjà existant",
            pre,
        )

    def test_create_computer_prevalidation_never_writes_ad(self):
        pre = before_simulation(
            function_body(
                "Invoke-EitasAdAdminCreateComputer"
            )
        )

        for command in (
            "New-ADComputer",
            "Set-ADComputer",
            "Remove-ADObject",
            "Rename-ADObject",
            "Move-ADObject",
        ):
            self.assertNotIn(
                command,
                pre,
                f"{command} found before Simulation return",
            )


if __name__ == "__main__":
    unittest.main()
