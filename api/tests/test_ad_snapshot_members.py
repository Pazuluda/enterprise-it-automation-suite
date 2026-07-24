from __future__ import annotations

import unittest

from app.services.ad_snapshot import (
    ADSnapshotBadRequest,
    _normalize_item,
    _normalize_snapshot,
)


BASE_DN = "DC=API,DC=LOCAL"


def make_item(**overrides):
    item = {
        "type": "group",
        "object_class": "group",
        "name": "GG_TEST",
        "distinguished_name": (
            "CN=GG_TEST,OU=EITAS,DC=API,DC=LOCAL"
        ),
        "members": None,
        "member_count": None,
        "member_of": None,
    }

    item.update(overrides)
    return item


class SnapshotMembershipNormalizationTests(unittest.TestCase):
    def test_unknown_members_remain_unknown(self):
        normalized = _normalize_item(
            make_item(
                members=None,
                member_count=999,
            ),
            BASE_DN,
        )

        self.assertIsNone(normalized["members"])
        self.assertIsNone(normalized["member_count"])
        self.assertEqual(normalized["member_of"], [])

    def test_missing_members_remain_unknown(self):
        item = make_item()
        item.pop("members")
        item.pop("member_count")

        normalized = _normalize_item(
            item,
            BASE_DN,
        )

        self.assertIsNone(normalized["members"])
        self.assertIsNone(normalized["member_count"])

    def test_known_members_are_cleaned_and_counted(self):
        normalized = _normalize_item(
            make_item(
                members=[
                    " CN=User1,OU=EITAS,DC=API,DC=LOCAL ",
                    "",
                    None,
                    "CN=User2,OU=EITAS,DC=API,DC=LOCAL",
                ],
                member_count=999,
            ),
            BASE_DN,
        )

        self.assertEqual(
            normalized["members"],
            [
                "CN=User1,OU=EITAS,DC=API,DC=LOCAL",
                "CN=User2,OU=EITAS,DC=API,DC=LOCAL",
            ],
        )
        self.assertEqual(normalized["member_count"], 2)

    def test_member_of_is_still_normalized(self):
        normalized = _normalize_item(
            make_item(
                member_of=[
                    " CN=Parent,OU=EITAS,DC=API,DC=LOCAL ",
                    "",
                ],
            ),
            BASE_DN,
        )

        self.assertEqual(
            normalized["member_of"],
            [
                "CN=Parent,OU=EITAS,DC=API,DC=LOCAL",
            ],
        )

    def test_invalid_members_value_is_rejected(self):
        with self.assertRaises(ADSnapshotBadRequest):
            _normalize_item(
                make_item(
                    members={
                        "unexpected": "value",
                    },
                ),
                BASE_DN,
            )

    def test_full_snapshot_preserves_known_and_unknown_states(self):
        payload = {
            "version": "2026-07-24T20:50:00.000Z",
            "generated_at": "2026-07-24T20:50:00.000Z",
            "domain": "API.LOCAL",
            "base_dn": BASE_DN,
            "controller": "SRV-DC01",
            "items": [
                make_item(
                    name="GG_UNKNOWN",
                    distinguished_name=(
                        "CN=GG_UNKNOWN,OU=EITAS,"
                        "DC=API,DC=LOCAL"
                    ),
                    members=None,
                ),
                make_item(
                    name="GG_KNOWN",
                    distinguished_name=(
                        "CN=GG_KNOWN,OU=EITAS,"
                        "DC=API,DC=LOCAL"
                    ),
                    members=[
                        "CN=User1,OU=EITAS,DC=API,DC=LOCAL",
                    ],
                ),
            ],
        }

        normalized = _normalize_snapshot(
            payload,
            BASE_DN,
        )

        by_name = {
            item["name"]: item
            for item in normalized["items"]
        }

        self.assertIsNone(
            by_name["GG_UNKNOWN"]["members"]
        )
        self.assertIsNone(
            by_name["GG_UNKNOWN"]["member_count"]
        )

        self.assertEqual(
            by_name["GG_KNOWN"]["members"],
            [
                "CN=User1,OU=EITAS,DC=API,DC=LOCAL",
            ],
        )
        self.assertEqual(
            by_name["GG_KNOWN"]["member_count"],
            1,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
