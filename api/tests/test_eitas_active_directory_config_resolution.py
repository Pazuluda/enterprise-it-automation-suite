from pathlib import Path
import unittest


MODULE = Path(__file__).resolve().parents[2] / "agent-windows" / "modules" / "EitasActiveDirectory.ps1"


class EitasActiveDirectoryConfigResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MODULE.read_text(encoding="utf-8")
        start = cls.source.index("function Get-EitasAdDomainDn {")
        middle = cls.source.index("function Get-EitasAllowedBaseDn {", start)
        end = cls.source.index("function Test-EitasDnSafe {", middle)
        cls.domain_block = cls.source[start:middle]
        cls.allowed_block = cls.source[middle:end]

    def test_domain_resolution_is_strict_mode_safe(self):
        self.assertIn("$Config.PSObject.Properties[$Name]", self.domain_block)
        self.assertNotIn("if ($Config.DomainDn)", self.domain_block)
        self.assertNotIn("if ($Config.BaseDn)", self.domain_block)

    def test_allowed_base_resolution_is_strict_mode_safe(self):
        self.assertIn("$Config.PSObject.Properties[$Name]", self.allowed_block)
        self.assertNotIn("if ($Config.AllowedBaseDn)", self.allowed_block)
        self.assertNotIn("if ($Config.EitasBaseDn)", self.allowed_block)

    def test_live_eitas_base_ou_property_is_supported(self):
        self.assertIn(chr(34) + "EitasBaseOu" + chr(34), self.allowed_block)

    def test_fallbacks_are_preserved(self):
        self.assertIn("Get-EitasAdDomainInfo", self.domain_block)
        self.assertIn("Get-EitasAdDomainDn -Config $Config", self.allowed_block)
        self.assertIn("return " + chr(34) + "OU=EITAS,$DomainDn" + chr(34), self.allowed_block)


if __name__ == "__main__":
    unittest.main()
