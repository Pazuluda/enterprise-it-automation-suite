from __future__ import annotations

import unittest

from app.services.ldap_attribute_policy import (
    C1_SCHEMA_BACKED_CANONICAL_PROPERTIES,
    C1_VIRTUAL_CANONICAL_PROPERTIES,
    resolve_ldap_attribute_policy,
)


class LDAPAttributeRepresentationTests(unittest.TestCase):
    def test_schema_and_virtual_counts(self):
        self.assertEqual(len(C1_SCHEMA_BACKED_CANONICAL_PROPERTIES), 45)
        self.assertEqual(len(C1_VIRTUAL_CANONICAL_PROPERTIES), 3)
        self.assertFalse(
            C1_SCHEMA_BACKED_CANONICAL_PROPERTIES
            & C1_VIRTUAL_CANONICAL_PROPERTIES
        )

    def test_virtual_properties_are_explicit(self):
        self.assertEqual(
            C1_VIRTUAL_CANONICAL_PROPERTIES,
            frozenset({
                "groupCategory",
                "groupScope",
                "protectedFromAccidentalDeletion",
            }),
        )

        for attribute_name in C1_VIRTUAL_CANONICAL_PROPERTIES:
            with self.subTest(attribute_name=attribute_name):
                decision = resolve_ldap_attribute_policy(attribute_name)
                self.assertEqual(decision.representation, "virtual")
                self.assertFalse(decision.schema_backed)
                self.assertTrue(decision.visible)
                self.assertFalse(
                    decision.generic_ldap_editor_editable
                )
                self.assertTrue(
                    decision.generic_ldap_editor_read_only
                )

    def test_schema_backed_properties_are_explicit(self):
        for attribute_name in C1_SCHEMA_BACKED_CANONICAL_PROPERTIES:
            with self.subTest(attribute_name=attribute_name):
                decision = resolve_ldap_attribute_policy(attribute_name)
                self.assertEqual(decision.representation, "schema")
                self.assertTrue(decision.schema_backed)
                self.assertTrue(decision.visible)
                self.assertFalse(
                    decision.generic_ldap_editor_editable
                )

    def test_denied_attribute_has_denied_representation(self):
        decision = resolve_ldap_attribute_policy(
            "extensionAttribute15"
        )

        self.assertEqual(decision.representation, "denied")
        self.assertFalse(decision.schema_backed)
        self.assertTrue(decision.denied)


if __name__ == "__main__":
    unittest.main()
