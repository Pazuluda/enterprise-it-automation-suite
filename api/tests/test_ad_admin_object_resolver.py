from pathlib import Path
import unittest


SOURCE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
).read_text(encoding="utf-8")


def resolver_body() -> str:
    start = SOURCE.index("function Resolve-EitasAdAdminObject {")
    end = SOURCE.index("\nfunction ", start + 1)
    return SOURCE[start:end]


class AdAdminObjectResolverTests(unittest.TestCase):
    def setUp(self):
        self.body = resolver_body()

    def test_fallback_uses_canonical_domain_dn_helper(self):
        self.assertIn(
            "Get-EitasAdDomainDn -Config $Config",
            self.body,
        )
        self.assertNotIn(
            'Get-EitasObjectValue -Object $Config -Names @("AdBaseDn", "BaseDn", "DomainDn")',
            self.body,
        )

    def test_fallback_search_uses_resolved_search_base(self):
        self.assertIn("-SearchBase $SearchBase", self.body)
        self.assertIn("-LDAPFilter", self.body)

    def test_fallback_preserves_clean_not_found_and_ambiguous_errors(self):
        self.assertIn("Objet AD introuvable", self.body)
        self.assertIn("Plusieurs objets AD correspondent", self.body)


if __name__ == "__main__":
    unittest.main()
