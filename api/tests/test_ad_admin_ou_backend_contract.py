from pathlib import Path
import unittest


SOURCE = Path("api/app/services/ad_admin.py").read_text(encoding="utf-8")


def create_ou_branch() -> str:
    start = SOURCE.index('    elif action in {"create_ou", "create_group"}:')
    end = SOURCE.index('    elif action == "create_user":', start)
    return SOURCE[start:end]


class OuBackendContractTests(unittest.TestCase):
    def setUp(self):
        self.branch = create_ou_branch()

    def test_create_ou_is_an_allowed_action(self):
        allowed_start = SOURCE.index("ALLOWED_ACTIONS = {")
        allowed_end = SOURCE.index("}", allowed_start)
        allowed_block = SOURCE[allowed_start:allowed_end]
        self.assertIn('"create_ou"', allowed_block)

    def test_create_ou_validates_parent_name_and_description(self):
        self.assertIn(
            'parent_dn = validate_dn(payload.get("parent_dn"), "parent_dn")',
            self.branch,
        )
        self.assertIn(
            'name = validate_name(payload.get("name"), "name")',
            self.branch,
        )
        self.assertIn(
            'description = clean_string(payload.get("description"))',
            self.branch,
        )

    def test_create_ou_normalized_payload_contains_only_common_creation_fields(self):
        expected = (
            '"parent_dn": parent_dn',
            '"name": name',
            '"description": description',
        )
        for item in expected:
            self.assertIn(item, self.branch)

        group_guard = self.branch.index('if action == "create_group":')
        common = self.branch[:group_guard]
        for group_only in (
            "sam_account_name",
            "group_scope",
            "group_category",
        ):
            self.assertNotIn(group_only, common)

    def test_create_ou_audit_keeps_identity_without_description_content(self):
        audit_start = self.branch.index("audit_details.update({")
        audit_end = self.branch.index("})", audit_start)
        audit = self.branch[audit_start:audit_end]
        self.assertIn('"parent_dn": parent_dn', audit)
        self.assertIn('"name": name', audit)
        self.assertNotIn('"description"', audit)


if __name__ == "__main__":
    unittest.main()
