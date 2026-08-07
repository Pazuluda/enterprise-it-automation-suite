import json
from pathlib import Path
import tempfile
import unittest

from app.services.ad_admin import (
    ADAdminBadRequest,
    ALLOWED_ACTIONS,
    create_ad_admin_job,
)


ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "agent-windows" / "modules" / "EitasAdAdmin.ps1"


def extract_function(source: str, name: str) -> str:
    marker = f"function {name} {{"
    start = source.index(marker)
    end = source.find("\nfunction ", start + len(marker))
    return source[start:] if end == -1 else source[start:end]


class ADAdminPrimaryGroupSimulationWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKER.read_text(encoding="utf-8")
        cls.function = extract_function(
            cls.source,
            "Invoke-EitasAdAdminSetPrimaryGroup",
        )
        cls.dispatcher = extract_function(
            cls.source,
            "Invoke-EitasAdAdminJob",
        )

    def create_job(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            jobs_file = Path(directory) / "ad-admin-jobs.json"
            response, audit = create_ad_admin_job(
                jobs_file,
                payload,
            )
            persisted_jobs = json.loads(
                jobs_file.read_text(encoding="utf-8")
            )

        self.assertEqual(len(persisted_jobs), 1)
        return response, audit, persisted_jobs[0]

    def test_feature_is_api_enabled(self):
        self.assertIn("set_primary_group", ALLOWED_ACTIONS)

    def test_feature_is_dispatched_to_simulation_function(self):
        self.assertIn('"set_primary_group" {', self.dispatcher)
        self.assertIn(
            (
                "return Invoke-EitasAdAdminSetPrimaryGroup "
                "-Config $Config -Payload $Payload -Mode $Mode"
            ),
            self.dispatcher,
        )

    def test_api_contract_persists_only_object_and_group_identity(self):
        response, audit, persisted_job = self.create_job({
            "action": "set_primary_group",
            "object_identity": "CN=Primary User,OU=Users,DC=API,DC=LOCAL",
            "group_identity": "CN=Primary Group,OU=Groups,DC=API,DC=LOCAL",
            "member_identity": "MUST-NOT-BE-PERSISTED",
            "created_by": "c43c3b2-test",
        })

        expected_payload = {
            "object_identity": "CN=Primary User,OU=Users,DC=API,DC=LOCAL",
            "group_identity": "CN=Primary Group,OU=Groups,DC=API,DC=LOCAL",
        }

        self.assertEqual(persisted_job["action"], "set_primary_group")
        self.assertEqual(persisted_job["payload"], expected_payload)
        self.assertEqual(response["job"]["payload"], expected_payload)
        self.assertNotIn("member_identity", persisted_job["payload"])

        self.assertEqual(audit["action"], "ad_admin_job_created")
        self.assertEqual(audit["request_id"], persisted_job["id"])
        self.assertEqual(audit["actor"], "c43c3b2-test")
        self.assertEqual(
            audit["details"],
            {
                "action": "set_primary_group",
                "object_identity": expected_payload["object_identity"],
                "group_identity": expected_payload["group_identity"],
                "job_id": persisted_job["id"],
            },
        )

    def test_object_identity_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs_file = Path(directory) / "ad-admin-jobs.json"
            with self.assertRaisesRegex(
                ADAdminBadRequest,
                "object_identity est obligatoire",
            ):
                create_ad_admin_job(
                    jobs_file,
                    {
                        "action": "set_primary_group",
                        "group_identity": "Domain Users",
                    },
                )

    def test_group_identity_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs_file = Path(directory) / "ad-admin-jobs.json"
            with self.assertRaisesRegex(
                ADAdminBadRequest,
                "group_identity est obligatoire",
            ):
                create_ad_admin_job(
                    jobs_file,
                    {
                        "action": "set_primary_group",
                        "object_identity": "primary.user",
                    },
                )

    def test_object_identity_aliases_are_normalized(self):
        aliases = (
            ("objectIdentity", "object-camel"),
            ("object_dn", "CN=Object DN,DC=API,DC=LOCAL"),
            ("objectDn", "CN=Object Camel DN,DC=API,DC=LOCAL"),
            ("distinguished_name", "CN=Distinguished,DC=API,DC=LOCAL"),
            ("distinguishedName", "CN=Distinguished Camel,DC=API,DC=LOCAL"),
            ("dn", "CN=DN,DC=API,DC=LOCAL"),
            ("sam_account_name", "sam-object"),
            ("samAccountName", "sam-camel-object"),
            ("username", "username-object"),
            ("name", "name-object"),
        )

        for alias, value in aliases:
            with self.subTest(alias=alias):
                _, _, persisted_job = self.create_job({
                    "action": "set_primary_group",
                    alias: value,
                    "group_identity": "Domain Users",
                })
                self.assertEqual(
                    persisted_job["payload"]["object_identity"],
                    value,
                )

    def test_group_identity_aliases_are_normalized(self):
        aliases = (
            ("groupIdentity", "group-camel"),
            ("group_dn", "CN=Group DN,DC=API,DC=LOCAL"),
            ("groupDn", "CN=Group Camel DN,DC=API,DC=LOCAL"),
            ("group_name", "group-name"),
            ("groupName", "group-camel-name"),
            ("group", "group-short"),
        )

        for alias, value in aliases:
            with self.subTest(alias=alias):
                _, _, persisted_job = self.create_job({
                    "action": "set_primary_group",
                    "object_identity": "primary.user",
                    alias: value,
                })
                self.assertEqual(
                    persisted_job["payload"]["group_identity"],
                    value,
                )

    def test_production_is_refused_before_object_resolution(self):
        production = self.function.index('if ($Mode -eq "Production")')
        resolver = self.function.index("Resolve-EitasAdAdminMember")
        self.assertLess(production, resolver)
        self.assertIn(
            "disponible uniquement en mode Simulation",
            self.function,
        )

    def test_function_contains_no_ad_write_command(self):
        for forbidden in (
            "Set-ADObject",
            "Set-ADUser",
            "Set-ADComputer",
            "Add-ADGroupMember",
            "Remove-ADGroupMember",
        ):
            self.assertNotIn(forbidden, self.function)

    def test_only_user_and_computer_subjects_are_supported(self):
        self.assertIn('$ObjectClass -eq "user"', self.function)
        self.assertIn('$ObjectClass -eq "computer"', self.function)
        self.assertIn("-Properties primaryGroupID", self.function)

    def test_target_group_must_be_security_and_same_domain(self):
        self.assertIn(
            '$TargetGroup.GroupCategory -ne "Security"',
            self.function,
        )
        self.assertIn(
            "$Subject.SID.AccountDomainSid.Value",
            self.function,
        )
        self.assertIn(
            "$TargetGroup.SID.AccountDomainSid.Value",
            self.function,
        )
        self.assertIn(
            "$SubjectDomainSid -ine $GroupDomainSid",
            self.function,
        )

    def test_target_rid_and_idempotency_are_resolved_before_membership(self):
        rid = self.function.index("$TargetPrimaryGroupId")
        already = self.function.index("$AlreadyPrimary")
        membership = self.function.index("Get-ADGroupMember")
        self.assertLess(rid, already)
        self.assertLess(already, membership)
        self.assertIn(
            "if (-not $AlreadyPrimary)",
            self.function,
        )

    def test_new_primary_group_requires_direct_membership(self):
        self.assertIn("Get-ADGroupMember", self.function)
        self.assertIn(
            "$DirectMember = $Existing.Count -gt 0",
            self.function,
        )
        self.assertIn(
            "doit etre membre direct du groupe cible",
            self.function,
        )

    def test_simulation_result_is_explicit_and_non_authorizing(self):
        for expected in (
            'action = "set_primary_group"',
            "simulated = $true",
            "production_authorized = $false",
            "already_primary = $AlreadyPrimary",
            "current_primary_group_id = $CurrentPrimaryGroupId",
            "target_group_id = $TargetPrimaryGroupId",
        ):
            self.assertIn(expected, self.function)


if __name__ == "__main__":
    unittest.main()
