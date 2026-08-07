from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
).read_text(encoding="utf-8")


def extract_function(name: str) -> str:
    marker = f"function {name} {{"
    start = SOURCE.index(marker)

    end = SOURCE.find(
        "\nfunction ",
        start + len(marker),
    )

    if end < 0:
        return SOURCE[start:]

    return SOURCE[start:end]


class ADAdminRemoveGroupMemberWorkerTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.remove = extract_function(
            "Invoke-EitasAdAdminRemoveGroupMember"
        )

    def test_group_is_resolved_before_simulation(self):
        resolver = self.remove.index(
            "Resolve-EitasAdAdminGroup"
        )
        simulation = self.remove.index(
            'if ($Mode -ne "Production")'
        )

        self.assertLess(
            resolver,
            simulation,
        )

    def test_member_is_resolved_before_simulation(self):
        resolver = self.remove.index(
            "Resolve-EitasAdAdminMember"
        )
        simulation = self.remove.index(
            'if ($Mode -ne "Production")'
        )

        self.assertLess(
            resolver,
            simulation,
        )

    def test_direct_membership_is_checked_before_simulation(self):
        membership = self.remove.index(
            "Get-ADGroupMember"
        )
        simulation = self.remove.index(
            'if ($Mode -ne "Production")'
        )

        self.assertLess(
            membership,
            simulation,
        )

    def test_simulation_exposes_real_membership_state(self):
        simulation = self.remove[
            self.remove.index(
                'if ($Mode -ne "Production")'
            ):
            self.remove.index(
                'if (-not $WasMember)'
            )
        ]

        self.assertIn(
            "simulated = $true",
            simulation,
        )
        self.assertIn(
            "was_member = $WasMember",
            simulation,
        )
        self.assertIn(
            "group_dn = $Group.DistinguishedName",
            simulation,
        )
        self.assertIn(
            "member_dn = $Member.DistinguishedName",
            simulation,
        )

    def test_simulation_contains_no_ad_write(self):
        prefix = self.remove[
            :self.remove.index(
                'if (-not $WasMember)'
            )
        ]

        self.assertNotIn(
            "Remove-ADGroupMember",
            prefix,
        )

    def test_production_absent_member_is_idempotent(self):
        self.assertIn(
            'if (-not $WasMember)',
            self.remove,
        )
        self.assertIn(
            "was_member = $false",
            self.remove,
        )

        absent = self.remove[
            self.remove.index(
                'if (-not $WasMember)'
            ):
            self.remove.index(
                "Remove-ADGroupMember"
            )
        ]

        self.assertNotIn(
            "Remove-ADGroupMember",
            absent,
        )

    def test_real_removal_remains_production_only(self):
        simulation = self.remove.index(
            'if ($Mode -ne "Production")'
        )
        removal = self.remove.index(
            "Remove-ADGroupMember"
        )

        self.assertLess(
            simulation,
            removal,
        )

    def test_group_members_are_supported_without_type_block(self):
        self.assertNotIn(
            'ObjectClass -ine "group"',
            self.remove,
        )
        self.assertIn(
            "Resolve-EitasAdAdminMember",
            self.remove,
        )


if __name__ == "__main__":
    unittest.main()
