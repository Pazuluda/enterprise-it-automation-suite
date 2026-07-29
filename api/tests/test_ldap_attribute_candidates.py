from __future__ import annotations

import unittest

from app.services.ldap_attribute_candidates import (
    C2_FIRST_WAVE_REVIEWED_CANDIDATES,
    LDAP_REVIEWED_CANDIDATE_POLICY_VERSION,
    LDAP_REVIEWED_CANDIDATE_STATUS,
    LDAP_REVIEWED_CANDIDATES_AUTHORIZE_WRITES,
    assert_reviewed_candidate_invariants,
    get_reviewed_ldap_candidate,
    list_reviewed_ldap_candidates,
)
from app.services.ldap_attribute_policy import (
    resolve_ldap_attribute_policy,
)


class LDAPReviewedCandidateTests(unittest.TestCase):
    def test_registry_contains_exactly_five_candidates(self):
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

    def test_registry_is_non_authorizing(self):
        self.assertEqual(
            LDAP_REVIEWED_CANDIDATE_POLICY_VERSION,
            "c2.3a.1",
        )
        self.assertEqual(
            LDAP_REVIEWED_CANDIDATE_STATUS,
            "reviewed_candidate_non_authorizing",
        )
        self.assertFalse(
            LDAP_REVIEWED_CANDIDATES_AUTHORIZE_WRITES
        )

        for candidate in C2_FIRST_WAVE_REVIEWED_CANDIDATES.values():
            with self.subTest(candidate=candidate.name):
                self.assertFalse(candidate.write_authorized)
                self.assertEqual(
                    candidate.required_roles,
                    frozenset({"ADAdmin", "UltraAdmin"}),
                )

    def test_class_scopes_are_restrictive(self):
        expected = {
            "employeeType": frozenset({"user"}),
            "preferredLanguage": frozenset({"user"}),
            "personalTitle": frozenset({"user", "contact"}),
            "middleName": frozenset({"user", "contact"}),
            "comment": frozenset({"user", "contact"}),
        }

        for name, classes in expected.items():
            with self.subTest(name=name):
                self.assertEqual(
                    C2_FIRST_WAVE_REVIEWED_CANDIDATES[
                        name
                    ].allowed_object_classes,
                    classes,
                )

    def test_length_limits_match_reviewed_matrix(self):
        expected = {
            "employeeType": (1, 256),
            "preferredLanguage": (0, 64),
            "personalTitle": (1, 64),
            "middleName": (0, 64),
            "comment": (0, 1024),
        }

        for name, limits in expected.items():
            with self.subTest(name=name):
                candidate = C2_FIRST_WAVE_REVIEWED_CANDIDATES[name]
                self.assertEqual(
                    (
                        candidate.minimum_length,
                        candidate.maximum_length,
                    ),
                    limits,
                )

    def test_lookup_is_case_insensitive(self):
        self.assertEqual(
            get_reviewed_ldap_candidate(
                " EMPLOYEETYPE "
            ).name,
            "employeeType",
        )
        self.assertEqual(
            get_reviewed_ldap_candidate(
                "preferredlanguage"
            ).name,
            "preferredLanguage",
        )
        self.assertIsNone(
            get_reviewed_ldap_candidate(
                "extensionAttribute15"
            )
        )
        self.assertIsNone(get_reviewed_ldap_candidate(None))

    def test_candidates_remain_denied_by_current_policy(self):
        for name in C2_FIRST_WAVE_REVIEWED_CANDIDATES:
            with self.subTest(name=name):
                decision = resolve_ldap_attribute_policy(name)
                self.assertTrue(decision.denied)
                self.assertFalse(decision.visible)
                self.assertFalse(
                    decision.generic_ldap_editor_editable
                )

    def test_catalog_is_sorted_and_non_authorizing(self):
        catalog = list_reviewed_ldap_candidates()
        names = [item["name"] for item in catalog]

        self.assertEqual(
            names,
            sorted(names, key=str.casefold),
        )
        self.assertEqual(len(catalog), 5)

        for item in catalog:
            self.assertEqual(
                item["status"],
                "reviewed_candidate_non_authorizing",
            )
            self.assertFalse(item["write_authorized"])

    def test_invariants(self):
        assert_reviewed_candidate_invariants()


if __name__ == "__main__":
    unittest.main()
