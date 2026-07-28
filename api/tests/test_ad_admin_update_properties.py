from __future__ import annotations

import unittest

from fastapi import HTTPException

from app.services.ad_admin import (
    ADAdminBadRequest,
    normalize_update_object_properties,
)


class UpdateObjectPropertiesNormalizationTests(
    unittest.TestCase
):
    def test_country_triplet_is_normalized(self):
        normalized = normalize_update_object_properties({
            "c": "fr",
            "co": " France ",
            "countryCode": "250",
        })

        self.assertEqual(
            normalized,
            {
                "c": "FR",
                "co": "France",
                "countryCode": 250,
            },
        )

    def test_country_aliases_are_supported(self):
        normalized = normalize_update_object_properties({
            "country_alpha2": "de",
            "country": " Allemagne ",
            "country_numeric_code": 276,
        })

        self.assertEqual(
            normalized,
            {
                "c": "DE",
                "co": "Allemagne",
                "countryCode": 276,
            },
        )

    def test_country_triplet_can_be_cleared(self):
        normalized = normalize_update_object_properties({
            "c": "",
            "co": "",
            "countryCode": "",
        })

        self.assertEqual(
            normalized,
            {
                "c": "",
                "co": "",
                "countryCode": "",
            },
        )

    def test_partial_country_triplet_is_rejected(self):
        with self.assertRaises(HTTPException):
            normalize_update_object_properties({
                "c": "FR",
                "co": "France",
            })

    def test_legacy_co_only_remains_supported(self):
        normalized = normalize_update_object_properties({
            "co": "France",
        })

        self.assertEqual(
            normalized,
            {"co": "France"},
        )

    def test_invalid_country_alpha2_is_rejected(self):
        with self.assertRaises(HTTPException):
            normalize_update_object_properties({
                "c": "FRA",
                "co": "France",
                "countryCode": 250,
            })

    def test_invalid_country_numeric_code_is_rejected(self):
        with self.assertRaises(HTTPException):
            normalize_update_object_properties({
                "c": "FR",
                "co": "France",
                "countryCode": "France",
            })

    def test_post_office_box_limit_is_enforced(self):
        normalized = normalize_update_object_properties({
            "postOfficeBox": "B" * 40,
        })

        self.assertEqual(
            normalized["postOfficeBox"],
            "B" * 40,
        )

        with self.assertRaises(HTTPException):
            normalize_update_object_properties({
                "postOfficeBox": "B" * 41,
            })

    def test_multi_value_post_office_box_is_rejected(self):
        with self.assertRaises(HTTPException):
            normalize_update_object_properties({
                "postOfficeBox": [
                    "BP 1",
                    "BP 2",
                ],
            })

    def test_manager_must_be_a_dn(self):
        with self.assertRaises(ADAdminBadRequest):
            normalize_update_object_properties({
                "manager": "Liam Ve",
            })

        manager_dn = (
            "CN=Liam Ve,OU=test,OU=Users,"
            "OU=EITAS,DC=API,DC=LOCAL"
        )

        normalized = normalize_update_object_properties({
            "manager": manager_dn,
        })

        self.assertEqual(
            normalized["manager"],
            manager_dn,
        )


    def test_profile_aliases_are_supported(self):
        normalized = normalize_update_object_properties({
            "profile_path":
                r"\\srv-fichiers\profils\liam",
            "script_path":
                "connexion.cmd",
            "home_directory":
                r"\\srv-fichiers\utilisateurs\liam",
            "home_drive":
                "h:",
        })

        self.assertEqual(
            normalized,
            {
                "profilePath":
                    r"\\srv-fichiers\profils\liam",
                "scriptPath":
                    "connexion.cmd",
                "homeDirectory":
                    r"\\srv-fichiers\utilisateurs\liam",
                "homeDrive":
                    "H:",
            },
        )

    def test_profile_properties_can_be_cleared(self):
        normalized = normalize_update_object_properties({
            "profilePath": "",
            "scriptPath": "",
            "homeDirectory": "",
            "homeDrive": "",
        })

        self.assertEqual(
            normalized,
            {
                "profilePath": "",
                "scriptPath": "",
                "homeDirectory": "",
                "homeDrive": "",
            },
        )

    def test_account_aliases_are_supported(self):
        normalized = normalize_update_object_properties({
            "user_principal_name":
                " liam.ve@api.local ",
            "account_expires":
                "2026-08-15",
        })

        self.assertEqual(
            normalized,
            {
                "userPrincipalName":
                    "liam.ve@api.local",
                "accountExpires":
                    "2026-08-15",
            },
        )

    def test_account_expiration_can_be_cleared(self):
        normalized = normalize_update_object_properties({
            "accountExpires": "",
        })

        self.assertEqual(
            normalized,
            {
                "accountExpires": "",
            },
        )

    def test_invalid_account_expiration_is_rejected(self):
        for value in [
            "15/08/2026",
            "2026-02-30",
            "2026-08-15 23:59:59",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(HTTPException):
                    normalize_update_object_properties({
                        "accountExpires": value,
                    })

    def test_invalid_user_principal_name_is_rejected(self):
        for value in [
            "",
            "liam.ve",
            "liam ve@api.local",
            "liam.ve@@api.local",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(HTTPException):
                    normalize_update_object_properties({
                        "userPrincipalName": value,
                    })


    def test_user_workstations_alias_is_normalized(self):
        normalized = normalize_update_object_properties({
            "user_workstations":
                " srv-dc01 ; PC-COMPTA-01, srv-dc01 ",
        })

        self.assertEqual(
            normalized,
            {
                "userWorkstations":
                    "SRV-DC01,PC-COMPTA-01",
            },
        )

    def test_user_workstations_can_be_cleared(self):
        normalized = normalize_update_object_properties({
            "userWorkstations": "",
        })

        self.assertEqual(
            normalized,
            {"userWorkstations": ""},
        )

    def test_invalid_user_workstations_are_rejected(self):
        for value in [
            "SRV DC01",
            "-SRV-DC01",
            "SRV-DC01-",
            "ABCDEFGHIJKLMNOP",
            ["SRV-DC01"],
        ]:
            with self.subTest(value=value):
                with self.assertRaises(HTTPException):
                    normalize_update_object_properties({
                        "userWorkstations": value,
                    })

    def test_logon_hours_alias_is_normalized(self):
        raw_value = "03," + ",".join(
            ["00"] * 20
        )

        normalized = normalize_update_object_properties({
            "logon_hours": raw_value,
        })

        self.assertEqual(
            normalized,
            {
                "logonHours":
                    "03 " + " ".join(["00"] * 20),
            },
        )

    def test_logon_hours_can_be_cleared(self):
        normalized = normalize_update_object_properties({
            "logonHours": "",
        })

        self.assertEqual(
            normalized,
            {"logonHours": ""},
        )

    def test_invalid_logon_hours_length_is_rejected(self):
        for value in [
            "00",
            " ".join(["00"] * 20),
            " ".join(["00"] * 22),
        ]:
            with self.subTest(value=value):
                with self.assertRaises(HTTPException):
                    normalize_update_object_properties({
                        "logonHours": value,
                    })

    def test_invalid_logon_hours_byte_is_rejected(self):
        values = ["00"] * 21
        values[10] = "GG"

        with self.assertRaises(HTTPException):
            normalize_update_object_properties({
                "logonHours": " ".join(values),
            })

    def test_direct_reports_is_read_only(self):
        for key in [
            "directReports",
            "direct_reports",
        ]:
            with self.subTest(key=key):
                with self.assertRaises(HTTPException):
                    normalize_update_object_properties({
                        key: [
                            "CN=Utilisateur,OU=Users,"
                            "OU=EITAS,DC=API,DC=LOCAL"
                        ],
                    })

    def test_invalid_home_drive_is_rejected(self):
        for value in [
            "H",
            "H:\\",
            "HOME:",
            "1:",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(HTTPException):
                    normalize_update_object_properties({
                        "homeDrive": value,
                    })


if __name__ == "__main__":
    unittest.main(verbosity=2)
