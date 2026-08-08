from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from app.services.ad_admin import (
    ADAdminBadRequest,
    create_ad_admin_job,
    validate_computer_name,
    validate_computer_target_ou,
)


VALID_OU = "OU=Computers,OU=EITAS,DC=API,DC=LOCAL"


class ComputerBackendContractTests(unittest.TestCase):
    def test_computer_name_is_normalized_to_uppercase(self):
        self.assertEqual(
            validate_computer_name(" pc-eitas-01 "),
            "PC-EITAS-01",
        )

    def test_computer_name_rejects_invalid_values(self):
        invalid_values = (
            "",
            "-PC01",
            "PC01-",
            "12345",
            "PC_EITAS",
            "PC-EITAS-1234567",
        )

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ADAdminBadRequest):
                    validate_computer_name(value)

    def test_target_ou_accepts_only_computers_eitas_scope(self):
        self.assertEqual(
            validate_computer_target_ou(VALID_OU),
            VALID_OU,
        )

        invalid_dns = (
            "CN=Computers,DC=API,DC=LOCAL",
            "OU=Servers,OU=EITAS,DC=API,DC=LOCAL",
            "OU=Computers,DC=API,DC=LOCAL",
        )

        for value in invalid_dns:
            with self.subTest(value=value):
                with self.assertRaises(ADAdminBadRequest):
                    validate_computer_target_ou(value)

    def test_create_computer_job_normalizes_payload(self):
        with TemporaryDirectory() as temp_dir:
            jobs_file = Path(temp_dir) / "jobs.json"

            create_ad_admin_job(
                jobs_file,
                {
                    "action": "create_computer",
                    "name": " pc-c51-01 ",
                    "target_ou_dn": VALID_OU,
                    "description": " Poste C5.1 ",
                    "location": " Lab ",
                    "enabled": False,
                    "created_by": "c5.1-test",
                },
            )

            data = json.loads(
                jobs_file.read_text(encoding="utf-8")
            )
            items = data if isinstance(data, list) else data.get("jobs", [])
            self.assertEqual(len(items), 1)

            payload = items[0]["payload"]

            self.assertEqual(payload["name"], "PC-C51-01")
            self.assertEqual(
                payload["sam_account_name"],
                "PC-C51-01$",
            )
            self.assertEqual(
                payload["target_ou_dn"],
                VALID_OU,
            )
            self.assertEqual(
                payload["description"],
                "Poste C5.1",
            )
            self.assertEqual(payload["location"], "Lab")
            self.assertFalse(payload["enabled"])

    def test_create_computer_job_enforces_text_limits(self):
        with TemporaryDirectory() as temp_dir:
            jobs_file = Path(temp_dir) / "jobs.json"

            with self.assertRaises(ADAdminBadRequest):
                create_ad_admin_job(
                    jobs_file,
                    {
                        "action": "create_computer",
                        "name": "PC-C51-02",
                        "target_ou_dn": VALID_OU,
                        "description": "D" * 1025,
                    },
                )

            with self.assertRaises(ADAdminBadRequest):
                create_ad_admin_job(
                    jobs_file,
                    {
                        "action": "create_computer",
                        "name": "PC-C51-03",
                        "target_ou_dn": VALID_OU,
                        "location": "L" * 129,
                    },
                )


if __name__ == "__main__":
    unittest.main()
