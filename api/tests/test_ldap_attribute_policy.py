from __future__ import annotations

import unittest

from app.services.ldap_attribute_policy import (
    C1_EDITABLE_ALIASES,
    C1_EDITABLE_CANONICAL_PROPERTIES,
    C1_EDITABLE_INPUT_KEYS,
    C1_PROPERTY_MAX_LENGTHS,
    C1_READ_ONLY_ALIASES,
    C1_READ_ONLY_CANONICAL_PROPERTIES,
    C1_VISIBLE_CANONICAL_PROPERTIES,
    LDAP_ATTRIBUTE_POLICY_DEFAULT,
    LDAP_ATTRIBUTE_POLICY_VERSION,
    LDAP_GENERIC_EDITOR_WRITES_ENABLED,
    LDAP_SCHEMA_CATALOG_IS_AUTHORIZATION,
    LDAPAttributePolicyError,
    assert_ldap_attribute_policy_invariants,
    get_c1_visible_ldap_policy_catalog,
    resolve_ldap_attribute_policy,
)


class LDAPAttributePolicyTests(unittest.TestCase):
    def test_validated_baseline_counts(self):
        self.assertEqual(len(C1_EDITABLE_INPUT_KEYS), 79)
        self.assertEqual(len(C1_EDITABLE_ALIASES), 32)
        self.assertEqual(
            len(set(C1_EDITABLE_ALIASES.values())),
            31,
        )
        self.assertEqual(
            len(C1_EDITABLE_CANONICAL_PROPERTIES),
            47,
        )
        self.assertEqual(
            len(C1_READ_ONLY_CANONICAL_PROPERTIES),
            1,
        )
        self.assertEqual(len(C1_READ_ONLY_ALIASES), 1)
        self.assertEqual(
            len(C1_VISIBLE_CANONICAL_PROPERTIES),
            48,
        )
        self.assertEqual(len(C1_PROPERTY_MAX_LENGTHS), 11)

    def test_policy_is_non_authorizing_and_default_deny(self):
        self.assertEqual(
            LDAP_ATTRIBUTE_POLICY_VERSION,
            "c2.2c.1",
        )
        self.assertEqual(LDAP_ATTRIBUTE_POLICY_DEFAULT, "deny")
        self.assertFalse(LDAP_SCHEMA_CATALOG_IS_AUTHORIZATION)
        self.assertFalse(LDAP_GENERIC_EDITOR_WRITES_ENABLED)

    def test_all_editable_input_keys_resolve_to_c1_canonical(self):
        for requested_name in C1_EDITABLE_INPUT_KEYS:
            with self.subTest(requested_name=requested_name):
                decision = resolve_ldap_attribute_policy(
                    requested_name
                )
                self.assertIn(
                    decision.canonical_name,
                    C1_EDITABLE_CANONICAL_PROPERTIES,
                )
                self.assertTrue(decision.known)
                self.assertTrue(decision.visible)
                self.assertTrue(
                    decision.c1_property_editor_editable
                )
                self.assertFalse(
                    decision.generic_ldap_editor_editable
                )
                self.assertTrue(
                    decision.generic_ldap_editor_read_only
                )
                self.assertFalse(decision.denied)

    def test_all_aliases_resolve_exactly(self):
        for alias, canonical_name in C1_EDITABLE_ALIASES.items():
            with self.subTest(alias=alias):
                decision = resolve_ldap_attribute_policy(alias)
                self.assertEqual(
                    decision.canonical_name,
                    canonical_name,
                )

    def test_upn_aliases_share_user_principal_name(self):
        self.assertEqual(
            resolve_ldap_attribute_policy(
                "upn"
            ).canonical_name,
            "userPrincipalName",
        )
        self.assertEqual(
            resolve_ldap_attribute_policy(
                "user_principal_name"
            ).canonical_name,
            "userPrincipalName",
        )

    def test_direct_reports_is_visible_read_only(self):
        for requested_name in (
            "directReports",
            "direct_reports",
            "DIRECTREPORTS",
        ):
            with self.subTest(requested_name=requested_name):
                decision = resolve_ldap_attribute_policy(
                    requested_name
                )
                self.assertEqual(
                    decision.canonical_name,
                    "directReports",
                )
                self.assertEqual(
                    decision.category,
                    "c1_read_only",
                )
                self.assertTrue(decision.known)
                self.assertTrue(decision.visible)
                self.assertFalse(
                    decision.c1_property_editor_editable
                )
                self.assertFalse(
                    decision.generic_ldap_editor_editable
                )
                self.assertTrue(
                    decision.generic_ldap_editor_read_only
                )
                self.assertFalse(decision.denied)

    def test_unknown_attribute_is_denied(self):
        decision = resolve_ldap_attribute_policy(
            "extensionAttribute15"
        )

        self.assertEqual(
            decision.canonical_name,
            "extensionAttribute15",
        )
        self.assertEqual(decision.category, "deny")
        self.assertFalse(decision.known)
        self.assertFalse(decision.visible)
        self.assertFalse(
            decision.c1_property_editor_editable
        )
        self.assertFalse(
            decision.generic_ldap_editor_editable
        )
        self.assertFalse(
            decision.generic_ldap_editor_read_only
        )
        self.assertTrue(decision.denied)

    def test_case_insensitive_resolution(self):
        lower = resolve_ldap_attribute_policy(
            "userprincipalname"
        )
        upper = resolve_ldap_attribute_policy(
            "USERPRINCIPALNAME"
        )

        self.assertEqual(
            lower.canonical_name,
            "userPrincipalName",
        )
        self.assertEqual(
            upper.canonical_name,
            "userPrincipalName",
        )

    def test_blank_or_non_string_name_is_rejected(self):
        for value in ("", "   ", None, 42, True):
            with self.subTest(value=value):
                with self.assertRaises(
                    LDAPAttributePolicyError
                ):
                    resolve_ldap_attribute_policy(value)

    def test_catalog_contains_48_sorted_read_only_entries(self):
        catalog = get_c1_visible_ldap_policy_catalog()

        self.assertEqual(len(catalog), 48)

        names = [
            item["canonical_name"]
            for item in catalog
        ]

        self.assertEqual(
            names,
            sorted(names, key=str.casefold),
        )
        self.assertEqual(len(names), len(set(names)))

        for item in catalog:
            self.assertTrue(item["known"])
            self.assertTrue(item["visible"])
            self.assertFalse(
                item["generic_ldap_editor_editable"]
            )
            self.assertTrue(
                item["generic_ldap_editor_read_only"]
            )
            self.assertFalse(item["denied"])

    def test_max_length_rules_target_c1_editable_properties(self):
        self.assertTrue(
            set(C1_PROPERTY_MAX_LENGTHS)
            <= C1_EDITABLE_CANONICAL_PROPERTIES
        )

    def test_policy_invariants(self):
        assert_ldap_attribute_policy_invariants()


if __name__ == "__main__":
    unittest.main()
