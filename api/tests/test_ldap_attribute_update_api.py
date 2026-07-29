import ast
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.models import LDAPAttributeUpdateValidationPayload
from app.services.ad_admin import ALLOWED_ACTIONS
from app.services.ldap_attribute_update import (
    LDAP_ATTRIBUTE_UPDATE_ACTION,
    LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED,
    normalize_ldap_attribute_update_request,
)


class LDAPAttributeUpdateAPIIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path("api/main.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        cls.function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "validate_ldap_attribute_update_payload"
        )

    def test_payload_model_accepts_complete_contract(self):
        payload = LDAPAttributeUpdateValidationPayload(
            action="update_ldap_attributes",
            object_identity=(
                "CN=Test,OU=Users,OU=EITAS,DC=API,DC=LOCAL"
            ),
            object_class="user",
            changes=[{
                "attribute_name": "employeeType",
                "operation": "set",
                "value": "Interne",
            }],
        )

        self.assertEqual(len(payload.changes), 1)

    def test_payload_model_requires_changes(self):
        with self.assertRaises(ValidationError):
            LDAPAttributeUpdateValidationPayload(
                action="update_ldap_attributes",
                object_identity=(
                    "CN=Test,OU=Users,OU=EITAS,DC=API,DC=LOCAL"
                ),
                object_class="user",
            )

    def test_route_uses_post_and_ad_access(self):
        decorator = next(
            item
            for item in self.function.decorator_list
            if isinstance(item, ast.Call)
            and isinstance(item.func, ast.Attribute)
            and item.func.attr == "post"
        )

        self.assertEqual(
            decorator.args[0].value,
            "/api/ad-explorer/ldap/update/validate",
        )

        arguments = self.function.args.args
        defaults = self.function.args.defaults
        default_map = dict(
            zip(
                (item.arg for item in arguments[-len(defaults):]),
                defaults,
            )
        )

        dependency = default_map["api_key"]

        self.assertEqual(dependency.func.id, "Depends")
        self.assertEqual(dependency.args[0].id, "AD_ACCESS")

    def test_route_never_creates_job_or_audit(self):
        rendered = ast.unparse(self.function)

        self.assertIn(
            "service_normalize_ldap_attribute_update_request",
            rendered,
        )
        self.assertIn("payload.model_dump()", rendered)
        self.assertIn(".to_dict()", rendered)
        self.assertIn("status_code=400", rendered)

        for forbidden in (
            "service_create_ad_admin_job",
            "write_audit_log",
            "AD_ADMIN_JOBS_FILE",
            "AD_EXPLORER_JOBS_FILE",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_normalized_request_is_not_executable(self):
        request = normalize_ldap_attribute_update_request({
            "action": "update_ldap_attributes",
            "object_identity": (
                "CN=Test,OU=Users,OU=EITAS,DC=API,DC=LOCAL"
            ),
            "object_class": "user",
            "changes": [{
                "attribute_name": "employeeType",
                "operation": "set",
                "value": "Interne",
            }],
        })

        self.assertFalse(request.execution_authorized)

    def test_action_remains_disabled(self):
        self.assertFalse(LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED)
        self.assertNotIn(
            LDAP_ATTRIBUTE_UPDATE_ACTION,
            ALLOWED_ACTIONS,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
