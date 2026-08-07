import unittest
from pathlib import Path


WORKER_PATH = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
)


def extract_function(source, name):
    marker = f"function {name} {{"

    start = source.index(marker)

    end = source.find(
        "\nfunction ",
        start + len(marker),
    )

    if end == -1:
        return source[start:]

    return source[start:end]


class ADAdminGroupMembershipWorkerTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKER_PATH.read_text(
            encoding="utf-8"
        )

        cls.safety = extract_function(
            cls.source,
            (
                "Assert-EitasAdAdmin"
                "GroupMembershipAdditionSafe"
            ),
        )

        cls.add_member = extract_function(
            cls.source,
            "Invoke-EitasAdAdminAddGroupMember",
        )

    def test_simulation_resolves_real_objects_first(self):
        group_index = self.add_member.index(
            "$Group = Resolve-EitasAdAdminGroup"
        )

        member_index = self.add_member.index(
            "$Member = Resolve-EitasAdAdminMember"
        )

        simulation_index = self.add_member.index(
            'if ($Mode -ne "Production")'
        )

        self.assertLess(
            group_index,
            simulation_index,
        )

        self.assertLess(
            member_index,
            simulation_index,
        )

    def test_self_membership_is_rejected(self):
        self.assertIn(
            (
                "[string]$Group.DistinguishedName -ieq"
            ),
            self.safety,
        )

        self.assertIn(
            (
                "[string]$Member.DistinguishedName"
            ),
            self.safety,
        )

        self.assertIn(
            (
                "Un groupe ne peut pas etre "
                "membre de lui-meme"
            ),
            self.safety,
        )

    def test_nested_group_cycle_is_rejected(self):
        self.assertIn(
            (
                '[string]$Member.ObjectClass '
                '-ieq'
            ),
            self.safety,
        )

        self.assertIn(
            '"group"',
            self.safety,
        )

        self.assertIn(
            (
                "Test-EitasAdAdmin"
                "GroupContainsGroup"
            ),
            self.safety,
        )

        self.assertIn(
            "-RootGroup $Member",
            self.safety,
        )

        self.assertIn(
            "-ExpectedGroup $Group",
            self.safety,
        )

        self.assertIn(
            "creerait un cycle entre groupes",
            self.safety,
        )

    def test_cycle_detection_walks_direct_groups(self):
        traversal = extract_function(
            self.source,
            (
                "Test-EitasAdAdmin"
                "GroupContainsGroup"
            ),
        )

        self.assertIn(
            "while ($Pending.Count -gt 0)",
            traversal,
        )

        self.assertIn(
            "$Visited = @{}",
            traversal,
        )

        self.assertIn(
            "Get-ADGroupMember `",
            traversal,
        )

        self.assertNotIn(
            "-Recursive",
            traversal,
        )

        self.assertIn(
            (
                "[string]$DirectMember."
                "ObjectClass"
            ),
            traversal,
        )

        self.assertIn(
            '"group"',
            traversal,
        )

        self.assertIn(
            "$ExpectedDn",
            traversal,
        )

    def test_existing_membership_stays_idempotent(self):
        existing_index = self.add_member.index(
            "$Existing = @("
        )

        simulation_index = self.add_member.index(
            'if ($Mode -ne "Production")'
        )

        self.assertLess(
            existing_index,
            simulation_index,
        )

        self.assertIn(
            "already_member = $true",
            self.add_member,
        )

    def test_simulation_returns_before_ad_write(self):
        simulation_index = self.add_member.index(
            'if ($Mode -ne "Production")'
        )

        write_index = self.add_member.index(
            "Add-ADGroupMember `"
        )

        self.assertLess(
            simulation_index,
            write_index,
        )

        simulation_block = self.add_member[
            simulation_index:write_index
        ]

        self.assertIn(
            "simulated = $true",
            simulation_block,
        )

        self.assertIn(
            "return [pscustomobject]@{",
            simulation_block,
        )

    def test_production_write_uses_resolved_dns(self):
        self.assertIn(
            (
                "-Identity "
                "$Group.DistinguishedName"
            ),
            self.add_member,
        )

        self.assertIn(
            (
                "-Members "
                "$Member.DistinguishedName"
            ),
            self.add_member,
        )


if __name__ == "__main__":
    unittest.main()
