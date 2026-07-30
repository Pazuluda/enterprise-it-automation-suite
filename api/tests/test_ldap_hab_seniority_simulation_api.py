from __future__ import annotations

import ast
from pathlib import Path
import unittest

from app.models import (
    LDAPHabSenioritySimulationPayload,
)
from app.services.ldap_attribute_candidates import (
    C2_FIRST_WAVE_REVIEWED_CANDIDATES,
    get_reviewed_ldap_candidate,
)
from app.services.ldap_hab_seniority_policy import (
    LDAP_HAB_SENIORITY_ATTRIBUTE_NAME,
)
from app.services.ldap_hab_seniority_simulation import (
    LDAPHabSimulationBadRequest,
    normalize_ldap_hab_simulation_request,
)


class LDAPHabSenioritySimulationApiTests(
    unittest.TestCase
):
    def payload(
        self,
        *,
        operation="set",
        value=100,
    ):
        return (
            LDAPHabSenioritySimulationPayload(
                action=(
                    "simulate_hab_seniority_index"
                ),
                object_identity=(
                    "CN=Test,OU=Users,"
                    "DC=EXAMPLE,DC=LOCAL"
                ),
                object_class="user",
                attribute_name=(
                    "msDS-HABSeniorityIndex"
                ),
                operation=operation,
                value=value,
            )
        )

    def test_model_preserves_integer(self):
        payload = self.payload(value=125)

        self.assertEqual(payload.value, 125)
        self.assertIs(type(payload.value), int)

    def test_simulation_validation_preserves_integer(self):
        payload = self.payload(value=125)

        request = (
            normalize_ldap_hab_simulation_request(
                payload.model_dump(),
                "Simulation",
            )
        )

        self.assertEqual(request.value, 125)
        self.assertIs(type(request.value), int)
        self.assertEqual(
            request.value_type,
            "integer32",
        )
        self.assertFalse(
            request.simulation_job_authorized
        )
        self.assertFalse(
            request.production_authorized
        )
        self.assertFalse(
            request.execution_authorized
        )

    def test_production_is_rejected(self):
        with self.assertRaisesRegex(
            LDAPHabSimulationBadRequest,
            "uniquement en mode Simulation",
        ):
            normalize_ldap_hab_simulation_request(
                self.payload().model_dump(),
                "Production",
            )

    def test_route_is_validation_only_and_rbac_protected(
        self,
    ):
        main_path = Path("api/main.py")
        source = main_path.read_text(
            encoding="utf-8"
        )
        tree = ast.parse(
            source,
            filename=str(main_path),
        )

        functions = [
            node
            for node in tree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name
            == (
                "validate_ldap_hab_"
                "seniority_simulation_payload"
            )
        ]

        self.assertEqual(len(functions), 1)

        function = functions[0]

        function_source = ast.get_source_segment(
            source,
            function,
        )

        decorator_source = "\n".join(
            ast.get_source_segment(
                source,
                decorator,
            )
            or ""
            for decorator in function.decorator_list
        )

        self.assertIn(
            "app.post",
            decorator_source,
        )
        self.assertIn(
            "hab-seniority/validate",
            source,
        )
        self.assertIn(
            "Depends(AD_ACCESS)",
            function_source,
        )
        self.assertNotIn(
            "AD_ADMIN_JOBS_FILE",
            function_source,
        )
        self.assertNotIn(
            "write_audit_log",
            function_source,
        )
        self.assertNotIn(
            "create_ldap_attribute_update_simulation_job",
            function_source,
        )

    def test_public_registry_remains_closed(self):
        self.assertEqual(
            len(
                C2_FIRST_WAVE_REVIEWED_CANDIDATES
            ),
            5,
        )

        self.assertIsNone(
            get_reviewed_ldap_candidate(
                LDAP_HAB_SENIORITY_ATTRIBUTE_NAME
            )
        )


if __name__ == "__main__":
    unittest.main()
