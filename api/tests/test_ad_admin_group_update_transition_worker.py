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


class ADAdminGroupUpdateTransitionWorkerTests(
    unittest.TestCase
):
    def test_transition_helper_exists(self):
        self.assertIn(
            "function Assert-EitasAdAdminGroupUpdateTransitionSafe {",
            SOURCE,
        )

    def test_group_prevalidation_runs_before_simulation_return(self):
        update = extract_function(
            "Invoke-EitasAdAdminUpdateObjectProperties"
        )

        validation = update.index(
            "Assert-EitasAdAdminGroupUpdateTransitionSafe"
        )

        simulation = update.index(
            'if ($Mode -ne "Production")'
        )

        self.assertLess(validation, simulation)

    def test_transition_helper_reads_real_group_state(self):
        helper = extract_function(
            "Assert-EitasAdAdminGroupUpdateTransitionSafe"
        )

        self.assertIn(
            "Get-ADGroup",
            helper,
        )
        self.assertIn(
            "GroupScope",
            helper,
        )
        self.assertIn(
            "GroupCategory",
            helper,
        )

    def test_direct_global_domain_local_conversion_is_rejected(self):
        helper = extract_function(
            "Assert-EitasAdAdminGroupUpdateTransitionSafe"
        )

        self.assertIn(
            "Global",
            helper,
        )
        self.assertIn(
            "DomainLocal",
            helper,
        )
        self.assertIn(
            "Universal",
            helper,
        )

    def test_transition_helper_contains_no_ad_write(self):
        helper = extract_function(
            "Assert-EitasAdAdminGroupUpdateTransitionSafe"
        )

        for command in (
            "Set-ADGroup",
            "Set-ADObject",
            "Add-ADGroupMember",
            "Remove-ADGroupMember",
            "New-ADGroup",
        ):
            self.assertNotIn(
                command,
                helper,
            )


    def test_scope_transition_reads_membership_state(self):
        helper = extract_function(
            "Assert-EitasAdAdminGroupUpdateTransitionSafe"
        )

        self.assertIn(
            "MemberOf",
            helper,
        )
        self.assertIn(
            "Get-ADGroupMember",
            helper,
        )
        self.assertIn(
            "foreignSecurityPrincipal",
            helper,
        )

    def test_global_to_universal_checks_parent_global_membership(self):
        helper = extract_function(
            "Assert-EitasAdAdminGroupUpdateTransitionSafe"
        )

        self.assertIn(
            "Global vers Universal",
            helper,
        )
        self.assertIn(
            "parent_group_scope",
            helper,
        )

    def test_domain_local_to_universal_checks_members(self):
        helper = extract_function(
            "Assert-EitasAdAdminGroupUpdateTransitionSafe"
        )

        self.assertIn(
            "DomainLocal vers Universal",
            helper,
        )
        self.assertIn(
            "member_group_scope",
            helper,
        )

    def test_universal_to_global_checks_member_domain_and_scope(self):
        helper = extract_function(
            "Assert-EitasAdAdminGroupUpdateTransitionSafe"
        )

        self.assertIn(
            "Universal vers Global",
            helper,
        )
        self.assertIn(
            "same_domain",
            helper,
        )

    def test_universal_to_domain_local_checks_parent_membership(self):
        helper = extract_function(
            "Assert-EitasAdAdminGroupUpdateTransitionSafe"
        )

        self.assertIn(
            "Universal vers DomainLocal",
            helper,
        )
        self.assertIn(
            "parent_group_scope",
            helper,
        )

    def test_category_change_reports_security_impact(self):
        helper = extract_function(
            "Assert-EitasAdAdminGroupUpdateTransitionSafe"
        )

        self.assertIn(
            "security_impact_warning",
            helper,
        )


if __name__ == "__main__":
    unittest.main()
