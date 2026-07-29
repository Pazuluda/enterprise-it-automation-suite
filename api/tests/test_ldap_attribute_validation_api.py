import ast
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.models import LDAPAttributeValidationPayload


class LDAPAttributeValidationAPIIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main_source = Path("api/main.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.main_source)
        cls.function = next(
            node
            for node in cls.tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "validate_ldap_attribute_request"
        )

    def test_payload_model_accepts_the_validation_contract(self):
        payload = LDAPAttributeValidationPayload(
            attribute_name="employeeType",
            object_class="user",
            operation="set",
            value="Interne",
        )
        self.assertEqual(payload.attribute_name, "employeeType")
        self.assertEqual(payload.operation, "set")

    def test_payload_model_requires_operation(self):
        with self.assertRaises(ValidationError):
            LDAPAttributeValidationPayload(
                attribute_name="comment",
                object_class="user",
            )

    def test_route_uses_post_path_and_ad_access(self):
        decorator = next(
            item
            for item in self.function.decorator_list
            if isinstance(item, ast.Call)
            and isinstance(item.func, ast.Attribute)
            and item.func.attr == "post"
        )
        self.assertEqual(
            decorator.args[0].value,
            "/api/ad-explorer/ldap/validate",
        )
        arguments = self.function.args.args
        defaults = self.function.args.defaults
        default_map = dict(
            zip((item.arg for item in arguments[-len(defaults):]), defaults)
        )
        dependency = default_map["api_key"]
        self.assertIsInstance(dependency, ast.Call)
        self.assertEqual(dependency.func.id, "Depends")
        self.assertEqual(dependency.args[0].id, "AD_ACCESS")

    def test_route_body_only_calls_the_validation_service(self):
        rendered = ast.unparse(self.function)
        self.assertIn(
            "service_validate_reviewed_ldap_attribute_request",
            rendered,
        )
        self.assertIn(".to_dict()", rendered)
        for forbidden in (
            "service_create_ad_admin_job",
            "service_create_ad_explorer_job",
            "write_audit_log",
            "AD_ADMIN_JOBS_FILE",
            "AD_EXPLORER_JOBS_FILE",
        ):
            self.assertNotIn(forbidden, rendered)


if __name__ == "__main__":
    unittest.main()
