import ast
import tempfile
import unittest
from pathlib import Path

from app.models import LDAPAttributeUpdateValidationPayload
from app.services.ad_admin import (
    ALLOWED_ACTIONS,
    create_ldap_attribute_update_simulation_job,
)
from app.services.ldap_attribute_update import (
    LDAP_ATTRIBUTE_UPDATE_ACTION,
    LDAPAttributeUpdateBadRequest,
)


class LDAPAttributeUpdateJobAPIIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path("api/main.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        cls.function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name
            == "create_ldap_attribute_update_simulation_job_api"
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
            "/api/ad-explorer/ldap/update/jobs",
        )

        arguments = self.function.args.args
        defaults = self.function.args.defaults

        default_map = dict(
            zip(
                (
                    item.arg
                    for item in arguments[-len(defaults):]
                ),
                defaults,
            )
        )

        dependency = default_map["api_key"]

        self.assertEqual(dependency.func.id, "Depends")
        self.assertEqual(dependency.args[0].id, "AD_ACCESS")

    def test_route_uses_runtime_mode_and_dedicated_constructor(self):
        rendered = ast.unparse(self.function)

        self.assertIn(
            "_eitas_agent_mode_load_config",
            rendered,
        )
        self.assertIn(
            "_eitas_agent_mode_normalize",
            rendered,
        )
        self.assertIn(
            "service_create_ldap_attribute_update_simulation_job",
            rendered,
        )
        self.assertNotIn(
            "service_create_ad_admin_job",
            rendered,
        )

        self.assertIn(
            "except LDAPAttributeUpdateBadRequest",
            rendered,
        )
        self.assertIn(
            "status_code=400",
            rendered,
        )

        constructor_position = rendered.index(
            "service_create_ldap_attribute_update_simulation_job"
        )
        audit_position = rendered.index("write_audit_log")

        self.assertLess(
            constructor_position,
            audit_position,
        )

    def test_production_refusal_creates_no_job_file(self):
        payload = LDAPAttributeUpdateValidationPayload(
            action="update_ldap_attributes",
            object_identity=(
                "CN=Test,OU=Users,OU=EITAS,"
                "DC=API,DC=LOCAL"
            ),
            object_class="user",
            changes=[{
                "attribute_name": "employeeType",
                "operation": "set",
                "value": "Interne",
            }],
        ).model_dump()

        with tempfile.TemporaryDirectory() as directory:
            jobs_file = Path(directory) / "jobs.json"

            with self.assertRaises(
                LDAPAttributeUpdateBadRequest
            ):
                create_ldap_attribute_update_simulation_job(
                    jobs_file,
                    payload,
                    "Production",
                )

            self.assertFalse(jobs_file.exists())

    def test_generic_ad_admin_action_remains_disabled(self):
        self.assertNotIn(
            LDAP_ATTRIBUTE_UPDATE_ACTION,
            ALLOWED_ACTIONS,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
