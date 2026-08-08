from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.services.ad_snapshot import receive_ad_snapshot


SNAPSHOT_SOURCE = Path(
    "agent-windows/modules/EitasAdSnapshot.ps1"
).read_text(encoding="utf-8")

LOOKUP_SOURCE = Path(
    "agent-windows/modules/EitasAdLookup.ps1"
).read_text(encoding="utf-8")


def function_body(source, name):
    marker = "function " + name + " {"
    start = source.index(marker)
    end = source.find(
        "\nfunction ",
        start + len(marker),
    )

    if end < 0:
        return source[start:]

    return source[start:end]



class ContainerDataPlaneTests(unittest.TestCase):
    def test_backend_snapshot_accepts_container(self):
        base_dn = "OU=EITAS,DC=API,DC=LOCAL"
        container_dn = (
            "CN=C54-SNAPSHOT," + base_dn
        )

        payload = {
            "version": "c5.4-test",
            "generated_at": "2026-08-08T12:00:00Z",
            "domain": "API.LOCAL",
            "base_dn": base_dn,
            "controller": "SRV-DC01",
            "items": [
                {
                    "type": "container",
                    "object_class": "container",
                    "name": "C54-SNAPSHOT",
                    "display_name": "C54-SNAPSHOT",
                    "distinguished_name": container_dn,
                    "dn": container_dn,
                    "description": "C5.4 snapshot",
                    "protected_from_accidental_deletion": True,
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"

            result = receive_ad_snapshot(
                path,
                payload,
                expected_base_dn=base_dn,
            )

            self.assertTrue(result["success"])

            persisted = json.loads(
                path.read_text(encoding="utf-8")
            )

        self.assertEqual(
            persisted["count"],
            1,
        )

        item = persisted["items"][0]

        self.assertEqual(
            item["type"],
            "container",
        )
        self.assertEqual(
            item["object_class"],
            "container",
        )
        self.assertEqual(
            item["distinguished_name"],
            container_dn,
        )
        self.assertTrue(
            item["protected_from_accidental_deletion"]
        )

    def test_snapshot_maps_and_collects_container(self):
        type_body = function_body(
            SNAPSHOT_SOURCE,
            "Get-EitasSnapshotObjectType",
        )

        convert_body = function_body(
            SNAPSHOT_SOURCE,
            "Convert-EitasSnapshotObject",
        )

        snapshot_body = function_body(
            SNAPSHOT_SOURCE,
            "New-EitasAdSnapshot",
        )

        self.assertIn(
            "\"container\" {" ,
            type_body,
        )
        self.assertIn(
            "return \"container\"",
            type_body,
        )
        self.assertIn(
            "\"container\"",
            convert_body,
        )
        self.assertIn(
            "ProtectedFromAccidentalDeletion",
            convert_body,
        )
        self.assertIn(
            "(objectClass=container)",
            snapshot_body,
        )

    def test_live_lookup_returns_container_children(self):
        body = function_body(
            LOOKUP_SOURCE,
            "Invoke-EitasAdExplorerListChildren",
        )

        self.assertIn(
            "(objectClass=container)",
            body,
        )
        self.assertIn(
            "$ObjectClass -eq \"container\"",
            body,
        )
        self.assertIn(
            "type = \"container\"",
            body,
        )
        self.assertIn(
            "object_class = \"container\"",
            body,
        )
        self.assertIn(
            "protected_from_accidental_deletion",
            body,
        )
        self.assertIn(
            "Contenu Active Directory chargé",
            body,
        )

    def test_live_lookup_remains_one_level_generic(self):
        body = function_body(
            LOOKUP_SOURCE,
            "Invoke-EitasAdExplorerListChildren",
        )

        self.assertIn(
            "-SearchBase $BaseDn",
            body,
        )
        self.assertIn(
            "-SearchScope OneLevel",
            body,
        )
        self.assertIn(
            "\"ProtectedFromAccidentalDeletion\"",
            body,
        )


if __name__ == "__main__":
    unittest.main()
