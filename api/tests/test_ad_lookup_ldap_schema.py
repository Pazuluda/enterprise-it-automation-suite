from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services.ad_jobs import (
    ADJobsBadRequest,
    claim_ad_lookup_job,
    create_ad_lookup_job,
    get_ad_lookup_job,
    submit_ad_lookup_job_result,
)


class AdLookupLdapSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.jobs_file = (
            Path(self.temp_directory.name)
            / "ad-lookup-jobs.json"
        )

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_existing_search_requires_query(self) -> None:
        with self.assertRaisesRegex(
            ADJobsBadRequest,
            "query est obligatoire",
        ):
            create_ad_lookup_job(
                self.jobs_file,
                {},
            )

    def test_unknown_action_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ADJobsBadRequest,
            "Action AD Lookup inconnue",
        ):
            create_ad_lookup_job(
                self.jobs_file,
                {
                    "action": "write_ldap_schema",
                },
            )

    def test_schema_job_is_read_only_request(self) -> None:
        response, audit = create_ad_lookup_job(
            self.jobs_file,
            {
                "action": "get_ldap_schema",
                "include_defunct": "false",
                "created_by": "c2-test",
            },
        )

        job = response["job"]

        self.assertEqual(
            job["action"],
            "get_ldap_schema",
        )
        self.assertEqual(job["query"], "")
        self.assertFalse(job["include_defunct"])
        self.assertEqual(job["status"], "pending")
        self.assertEqual(
            audit["details"]["action"],
            "get_ldap_schema",
        )

    def test_schema_result_keeps_count_and_read_only_audit(
        self,
    ) -> None:
        response, _ = create_ad_lookup_job(
            self.jobs_file,
            {
                "action": "get_ldap_schema",
                "include_defunct": False,
            },
        )
        job_id = response["job"]["id"]

        claim_ad_lookup_job(
            self.jobs_file,
            job_id,
            {
                "agent_name": "SRV-DC01",
            },
        )

        result_response, audit = (
            submit_ad_lookup_job_result(
                self.jobs_file,
                job_id,
                {
                    "success": True,
                    "message": (
                        "Catalogue LDAP charge "
                        "en lecture seule"
                    ),
                    "agent_name": "SRV-DC01",
                    "result": {
                        "action": "get_ldap_schema",
                        "read_only": True,
                        "count": 1507,
                        "items": [],
                    },
                },
            )
        )

        stored = get_ad_lookup_job(
            self.jobs_file,
            job_id,
        )

        self.assertEqual(
            result_response["job_id"],
            job_id,
        )
        self.assertEqual(stored["status"], "completed")
        self.assertTrue(stored["result"]["read_only"])
        self.assertEqual(stored["result"]["count"], 1507)
        self.assertEqual(
            audit["details"]["action"],
            "get_ldap_schema",
        )
        self.assertEqual(
            audit["details"]["count"],
            1507,
        )
        self.assertTrue(
            audit["details"]["read_only"],
        )


if __name__ == "__main__":
    unittest.main()
