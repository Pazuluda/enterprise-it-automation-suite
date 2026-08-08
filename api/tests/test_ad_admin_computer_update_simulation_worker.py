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


class ComputerUpdateSimulationTests(unittest.TestCase):
    def setUp(self):
        self.pre = before_simulation(
            function_body(
                "Invoke-EitasAdAdminUpdateObjectProperties"
            )
        )

    def test_computer_sam_is_validated_before_simulation(self):
        self.assertIn("$HasGroupSamChanges", self.pre)
        self.assertIn('"computer"', self.pre)
        self.assertIn("EndsWith(", self.pre)
        self.assertIn("$SamConflict = Get-ADObject", self.pre)

    def test_computer_system_properties_are_validated_before_simulation(self):
        self.assertIn("$HasComputerSystemChanges", self.pre)
        self.assertIn(
            "Les propriétés de système d’exploitation "
            "sont réservées aux ordinateurs",
            self.pre,
        )

    def test_accidental_deletion_policy_is_validated_before_simulation(self):
        self.assertIn(
            "$ProtectedFromAccidentalDeletion",
            self.pre,
        )
        self.assertIn(
            "La protection contre la suppression accidentelle "
            "est réservée",
            self.pre,
        )

    def test_update_prevalidation_contains_real_ad_conflict_reads(self):
        self.assertIn("Get-ADRootDSE", self.pre)
        self.assertIn("Get-ADObject", self.pre)

    def test_update_prevalidation_never_writes_ad(self):
        for command in (
            "Set-ADObject",
            "Set-ADUser",
            "Set-ADGroup",
            "Set-ADComputer",
            "Set-ADOrganizationalUnit",
            "Clear-ADAccountExpiration",
        ):
            self.assertNotIn(
                command,
                self.pre,
                f"{command} found before Simulation return",
            )


if __name__ == "__main__":
    unittest.main()
