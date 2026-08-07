from pathlib import Path
import unittest

SOURCE = Path(
    "agent-windows/modules/EitasAdLookup.ps1"
).read_text(encoding="utf-8-sig")

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

class ADLookupGroupMembersRecursiveWorkerTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.function = extract_function(
            "Invoke-EitasAdExplorerGetGroupMembers"
        )

    def test_recursive_mode_defaults_to_false(self):
        self.assertIn("$Recursive = $false", self.function)
        self.assertIn('"recursive",', self.function)
        self.assertIn('"include_nested",', self.function)

    def test_direct_lookup_remains_non_recursive(self):
        self.assertIn("Get-ADGroupMember", self.function)
        self.assertNotIn("-Recursive", self.function)

    def test_explicit_queue_traversal_is_used(self):
        self.assertIn("System.Collections.Queue", self.function)
        self.assertIn("$Queue.Enqueue(", self.function)
        self.assertIn("while ($Queue.Count -gt 0)", self.function)

    def test_cycles_and_duplicates_are_guarded(self):
        self.assertIn("$VisitedGroups = @{}", self.function)
        self.assertIn("$SeenMembers = @{}", self.function)
        self.assertIn("$VisitedGroups.ContainsKey", self.function)
        self.assertIn("$SeenMembers.ContainsKey", self.function)

    def test_recursive_traversal_keeps_scope_guard(self):
        self.assertGreaterEqual(
            self.function.count("Assert-EitasDnSafe"),
            2,
        )
        self.assertIn(
            "-DistinguishedName $NestedGroupDn",
            self.function,
        )

    def test_direct_items_have_explicit_metadata(self):
        self.assertIn("direct = $true", self.function)
        self.assertIn("depth = 1", self.function)
        self.assertIn(
            "parent_group_dn = [string]$Group.DistinguishedName",
            self.function,
        )

    def test_nested_items_have_explicit_metadata(self):
        self.assertIn("direct = $false", self.function)
        self.assertIn("depth = $Depth", self.function)
        self.assertIn(
            "parent_group_dn = $NestedGroupDn",
            self.function,
        )

    def test_result_exposes_recursive_counts(self):
        for marker in (
            "recursive = $Recursive",
            "direct_count = $DirectCount",
            "nested_count = $Members.Count - $DirectCount",
        ):
            self.assertIn(marker, self.function)

    def test_function_is_read_only(self):
        for command in (
            "Add-ADGroupMember",
            "Remove-ADGroupMember",
            "Set-ADGroup",
            "New-ADGroup",
            "Set-ADObject",
        ):
            self.assertNotIn(command, self.function)


    def test_limit_is_parsed_and_capped(self):
        for marker in (
            '"limit"',
            '"max_results"',
            '"maxResults"',
            "$Limit = 500",
            "[Math]::Min(",
            "$ParsedLimit,",
            "5000",
        ):
            self.assertIn(marker, self.function)

    def test_direct_loop_is_bounded_by_limit(self):
        direct_start = self.function.index(
            "foreach ($Member in $DirectMembers)"
        )
        queue_start = self.function.index(
            "if ($Recursive)"
        )
        direct_block = self.function[
            direct_start:queue_start
        ]

        self.assertIn(
            "$Items.Count -ge $Limit",
            direct_block,
        )
        self.assertIn(
            "$Truncated = $true",
            direct_block,
        )

    def test_recursive_queue_is_bounded_by_limit(self):
        queue_start = self.function.index(
            "while ($Queue.Count -gt 0)"
        )
        queue_block = self.function[queue_start:]

        self.assertIn(
            "$Items.Count -ge $Limit",
            queue_block,
        )
        self.assertIn(
            "$Truncated = $true",
            queue_block,
        )

    def test_result_exposes_limit_and_truncation(self):
        self.assertIn(
            "limit = $Limit",
            self.function,
        )
        self.assertIn(
            "truncated = $Truncated",
            self.function,
        )


if __name__ == "__main__":
    unittest.main()
