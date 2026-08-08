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


class ComputerRenameSimulationTests(unittest.TestCase):
    def test_computer_rename_detects_object_class_before_simulation(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminRenameObject")
        )

        self.assertIn("$Object.ObjectClass", pre)
        self.assertIn('$ObjectClass -eq "computer"', pre)

    def test_computer_rename_validates_computer_name_before_simulation(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminRenameObject")
        )

        self.assertIn("ToUpperInvariant()", pre)
        self.assertIn("^[A-Z0-9-]+$", pre)
        self.assertIn("StartsWith", pre)
        self.assertIn("EndsWith", pre)
        self.assertIn("^[0-9]+$", pre)

    def test_computer_rename_checks_sam_conflict_before_simulation(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminRenameObject")
        )

        self.assertIn("Get-ADComputer", pre)
        self.assertIn("$ComputerConflict", pre)
        self.assertIn("Un compte ordinateur utilise déjà", pre)

    def test_computer_rename_prevalidation_never_writes_ad(self):
        pre = before_simulation(
            function_body("Invoke-EitasAdAdminRenameObject")
        )

        for command in (
            "Rename-ADObject",
            "Set-ADComputer",
            "Move-ADObject",
            "Remove-ADObject",
        ):
            self.assertNotIn(
                command,
                pre,
                f"{command} found before Simulation return",
            )


if __name__ == "__main__":
    unittest.main()
