from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.ad_admin import (
    create_ldap_attribute_update_simulation_job,
)
from app.services.ldap_attribute_candidates import (
    C2_FIRST_WAVE_REVIEWED_CANDIDATES,
    LDAPReviewedCandidate,
)
from app.services.ldap_attribute_update import (
    normalize_ldap_attribute_update_request,
    prepare_ldap_attribute_update_simulation_payload,
)


ROLES = frozenset({
    "ADAdmin",
    "UltraAdmin",
})


BOOLEAN_CANDIDATE = LDAPReviewedCandidate(
    name="futureBoolean",
    value_type="boolean",
    allowed_object_classes=frozenset({
        "user",
    }),
    minimum_length=0,
    maximum_length=0,
    clearable=True,
    property_sets=(),
    required_roles=ROLES,
)


INTEGER_CANDIDATE = LDAPReviewedCandidate(
    name="futureInteger",
    value_type="integer32",
    allowed_object_classes=frozenset({
        "user",
    }),
    minimum_length=0,
    maximum_length=0,
    clearable=True,
    property_sets=(),
    required_roles=ROLES,
    minimum_value=0,
    maximum_value=100,
)


def candidate_for(attribute_name):
    normalized = str(
        attribute_name or ""
    ).strip().casefold()

    return {
        "futureboolean": BOOLEAN_CANDIDATE,
        "futureinteger": INTEGER_CANDIDATE,
    }.get(normalized)


def typed_request():
    return {
        "action": "update_ldap_attributes",
        "object_identity": (
            "CN=Test,OU=Users,OU=EITAS,"
            "DC=API,DC=LOCAL"
        ),
        "object_class": "user",
        "changes": [
            {
                "attribute_name": "futureBoolean",
                "operation": "set",
                "value": True,
            },
            {
                "attribute_name": "futureInteger",
                "operation": "set",
                "value": 42,
            },
        ],
        "created_by": "typed-unit-test",
    }


class LDAPTypedPipelineTests(unittest.TestCase):
    def test_normalizer_preserves_json_types(self):
        with patch(
            "app.services."
            "ldap_attribute_validation."
            "get_reviewed_ldap_candidate",
            side_effect=candidate_for,
        ):
            request = (
                normalize_ldap_attribute_update_request(
                    typed_request()
                )
            )

        changes = list(request.changes)

        self.assertIs(
            changes[0]["value"],
            True,
        )
        self.assertEqual(
            changes[0]["value_type"],
            "boolean",
        )

        self.assertEqual(
            changes[1]["value"],
            42,
        )
        self.assertIs(
            type(changes[1]["value"]),
            int,
        )
        self.assertEqual(
            changes[1]["value_type"],
            "integer32",
        )

        self.assertFalse(
            request.execution_authorized
        )

    def test_simulation_payload_preserves_types(self):
        with patch(
            "app.services."
            "ldap_attribute_validation."
            "get_reviewed_ldap_candidate",
            side_effect=candidate_for,
        ):
            payload = (
                prepare_ldap_attribute_update_simulation_payload(
                    typed_request(),
                    "Simulation",
                )
            )

        self.assertIs(
            payload["changes"][0]["value"],
            True,
        )
        self.assertEqual(
            payload["changes"][1]["value"],
            42,
        )
        self.assertIs(
            type(payload["changes"][1]["value"]),
            int,
        )

        self.assertTrue(
            payload["simulation_job_authorized"]
        )
        self.assertFalse(
            payload["production_authorized"]
        )
        self.assertFalse(
            payload["execution_authorized"]
        )

    def test_job_json_preserves_types_and_audit_redacts_values(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            jobs_file = Path(directory) / "jobs.json"

            with patch(
                "app.services."
                "ldap_attribute_validation."
                "get_reviewed_ldap_candidate",
                side_effect=candidate_for,
            ):
                response, audit = (
                    create_ldap_attribute_update_simulation_job(
                        jobs_file,
                        typed_request(),
                        "Simulation",
                    )
                )

            jobs = json.loads(
                jobs_file.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                len(jobs),
                1,
            )

            job_changes = (
                jobs[0]["payload"]["changes"]
            )

            self.assertIs(
                job_changes[0]["value"],
                True,
            )
            self.assertEqual(
                job_changes[0]["value_type"],
                "boolean",
            )

            self.assertEqual(
                job_changes[1]["value"],
                42,
            )
            self.assertIs(
                type(job_changes[1]["value"]),
                int,
            )
            self.assertEqual(
                job_changes[1]["value_type"],
                "integer32",
            )

            response_changes = (
                response["job"]["payload"]["changes"]
            )

            self.assertIs(
                response_changes[0]["value"],
                True,
            )
            self.assertEqual(
                response_changes[1]["value"],
                42,
            )

            self.assertEqual(
                audit["details"]["attribute_names"],
                [
                    "futureBoolean",
                    "futureInteger",
                ],
            )
            self.assertEqual(
                audit["details"]["change_count"],
                2,
            )
            self.assertNotIn(
                "changes",
                audit["details"],
            )
            self.assertNotIn(
                "value",
                audit["details"],
            )

            audit_text = json.dumps(
                audit,
                ensure_ascii=False,
            )

            self.assertNotIn(
                "futureBoolean\": true",
                audit_text,
            )
            self.assertNotIn(
                "futureInteger\": 42",
                audit_text,
            )

    def test_public_registry_remains_unchanged(self):
        self.assertEqual(
            set(C2_FIRST_WAVE_REVIEWED_CANDIDATES),
            {
                "employeeType",
                "preferredLanguage",
                "personalTitle",
                "middleName",
                "comment",
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
