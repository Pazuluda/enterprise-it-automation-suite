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


class ADAdminGroupScopeCompatibilityWorkerTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.resolver = extract_function(
            "Resolve-EitasAdAdminGroup"
        )

        cls.compatibility = extract_function(
            "Assert-EitasAdAdminGroupScopeCompatibility"
        )

        cls.safety = extract_function(
            "Assert-EitasAdAdminGroupMembershipAdditionSafe"
        )

        cls.add_member = extract_function(
            "Invoke-EitasAdAdminAddGroupMember"
        )

    def test_group_resolver_requests_scope(self):
        self.assertIn(
            "-Properties Description, GroupScope",
            self.resolver,
        )

    def test_non_group_members_are_unchanged(self):
        self.assertIn(
            '$MemberObjectClass -ine "group"',
            self.compatibility,
        )
        self.assertIn(
            "return $null",
            self.compatibility,
        )

    def test_member_group_scope_is_read_from_ad(self):
        self.assertIn(
            "Get-ADGroup `",
            self.compatibility,
        )
        self.assertIn(
            "-Properties GroupScope `",
            self.compatibility,
        )

    def test_global_target_only_accepts_global_group(self):
        block = self.compatibility[
            self.compatibility.index('"Global" {'):
            self.compatibility.index('"Universal" {')
        ]

        self.assertIn(
            '"Global"',
            block,
        )
        self.assertNotIn(
            '"Universal",',
            block,
        )
        self.assertNotIn(
            '"DomainLocal"',
            block,
        )

    def test_universal_target_accepts_global_and_universal(self):
        block = self.compatibility[
            self.compatibility.index('"Universal" {'):
            self.compatibility.index('"DomainLocal" {')
        ]

        self.assertIn(
            '"Global",',
            block,
        )
        self.assertIn(
            '"Universal"',
            block,
        )
        self.assertNotIn(
            '"DomainLocal"',
            block,
        )

    def test_domain_local_target_accepts_all_group_scopes(self):
        block = self.compatibility[
            self.compatibility.index('"DomainLocal" {'):
            self.compatibility.index("default {")
        ]

        for scope in (
            '"Global",',
            '"Universal",',
            '"DomainLocal"',
        ):
            self.assertIn(
                scope,
                block,
            )

    def test_incompatible_scope_is_rejected(self):
        self.assertIn(
            "$AllowedScopes -notcontains",
            self.compatibility,
        )
        self.assertIn(
            "Imbrication de groupes incompatible",
            self.compatibility,
        )

    def test_scope_check_runs_before_cycle_detection(self):
        compatibility_index = self.safety.index(
            "Assert-EitasAdAdminGroupScopeCompatibility"
        )

        cycle_index = self.safety.index(
            "$WouldCreateCycle"
        )

        self.assertLess(
            compatibility_index,
            cycle_index,
        )

    def test_scope_check_runs_before_simulation_return(self):
        safety_call = self.add_member.index(
            "Assert-EitasAdAdminGroupMembershipAdditionSafe"
        )

        simulation_branch = self.add_member.index(
            'if ($Mode -ne "Production")'
        )

        self.assertLess(
            safety_call,
            simulation_branch,
        )

    def test_scope_helper_contains_no_ad_write(self):
        for command in (
            "Add-ADGroupMember",
            "Remove-ADGroupMember",
            "Set-ADGroup",
            "New-ADGroup",
        ):
            self.assertNotIn(
                command,
                self.compatibility,
            )


if __name__ == "__main__":
    unittest.main()
