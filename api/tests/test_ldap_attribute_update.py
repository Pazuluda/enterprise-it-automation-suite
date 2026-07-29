from __future__ import annotations

import unittest

from app.services.ad_admin import ALLOWED_ACTIONS
from app.services.ldap_attribute_update import (
    LDAP_ATTRIBUTE_UPDATE_ACTION,
    LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED,
    LDAPAttributeUpdateBadRequest,
    assert_ldap_attribute_update_invariants,
    normalize_ldap_attribute_update_request,
)


class LDAPAttributeUpdateNormalizationTests(unittest.TestCase):
    def normalize(self, **overrides):
        payload = {
            "action": "update_ldap_attributes",
            "object_identity": (
                "CN=Test,OU=Users,OU=EITAS,DC=API,DC=LOCAL"
            ),
            "object_class": "user",
            "changes": [{
                "attribute_name": "employeeType",
                "operation": "set",
                "value": " Interne ",
            }],
        }
        payload.update(overrides)
        return normalize_ldap_attribute_update_request(payload)

    def test_valid_payload_is_normalized_but_not_executable(self):
        request = self.normalize()

        self.assertEqual(
            request.action,
            "update_ldap_attributes",
        )
        self.assertEqual(request.object_class, "user")
        self.assertFalse(request.execution_authorized)
        self.assertEqual(
            request.changes[0]["attribute_name"],
            "employeeType",
        )
        self.assertEqual(
            request.changes[0]["value"],
            "Interne",
        )
        self.assertFalse(
            request.changes[0]["write_authorized"]
        )

    def test_set_and_clear_can_share_one_job(self):
        request = self.normalize(changes=[
            {
                "attribute_name": "employeeType",
                "operation": "set",
                "value": "Interne",
            },
            {
                "attribute_name": "comment",
                "operation": "clear",
            },
        ])

        self.assertEqual(len(request.changes), 2)
        self.assertIsNone(request.changes[1]["value"])

    def test_contact_scope_is_supported_only_where_reviewed(self):
        request = self.normalize(
            object_class="contact",
            changes=[{
                "attribute_name": "personalTitle",
                "operation": "set",
                "value": "Dr",
            }],
        )

        self.assertEqual(request.object_class, "contact")

        with self.assertRaises(LDAPAttributeUpdateBadRequest):
            self.normalize(
                object_class="contact",
                changes=[{
                    "attribute_name": "employeeType",
                    "operation": "set",
                    "value": "Interne",
                }],
            )

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(LDAPAttributeUpdateBadRequest):
            self.normalize(action="update_object_properties")

    def test_object_identity_must_be_a_dn(self):
        with self.assertRaises(LDAPAttributeUpdateBadRequest):
            self.normalize(object_identity="Test")

    def test_changes_must_be_a_nonempty_list(self):
        for value in (None, {}, [], "employeeType"):
            with self.subTest(value=value):
                with self.assertRaises(
                    LDAPAttributeUpdateBadRequest
                ):
                    self.normalize(changes=value)

    def test_job_is_limited_to_five_changes(self):
        changes = [
            {
                "attribute_name": "comment",
                "operation": "set",
                "value": str(index),
            }
            for index in range(6)
        ]

        with self.assertRaises(LDAPAttributeUpdateBadRequest):
            self.normalize(changes=changes)

    def test_duplicate_attributes_are_rejected(self):
        with self.assertRaises(LDAPAttributeUpdateBadRequest):
            self.normalize(changes=[
                {
                    "attribute_name": "comment",
                    "operation": "set",
                    "value": "A",
                },
                {
                    "attribute_name": " COMMENT ",
                    "operation": "clear",
                },
            ])

    def test_unknown_attribute_is_rejected(self):
        with self.assertRaises(LDAPAttributeUpdateBadRequest):
            self.normalize(changes=[{
                "attribute_name": "extensionAttribute15",
                "operation": "set",
                "value": "test",
            }])

    def test_invalid_change_shape_is_rejected(self):
        with self.assertRaises(LDAPAttributeUpdateBadRequest):
            self.normalize(changes=["employeeType"])

    def test_serialization_remains_non_authorizing(self):
        payload = self.normalize().to_dict()

        self.assertFalse(payload["execution_authorized"])
        self.assertFalse(
            payload["changes"][0]["write_authorized"]
        )

    def test_action_is_not_enabled_in_ad_admin(self):
        self.assertFalse(LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED)
        self.assertNotIn(
            LDAP_ATTRIBUTE_UPDATE_ACTION,
            ALLOWED_ACTIONS,
        )
        assert_ldap_attribute_update_invariants()


if __name__ == "__main__":
    unittest.main(verbosity=2)
