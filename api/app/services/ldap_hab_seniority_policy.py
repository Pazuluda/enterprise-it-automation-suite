from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


LDAP_HAB_SENIORITY_POLICY_VERSION = "c2.6a.1"
LDAP_HAB_SENIORITY_ATTRIBUTE_NAME = (
    "msDS-HABSeniorityIndex"
)
LDAP_HAB_SENIORITY_POLICY_STATUS = (
    "reviewed_policy_dormant_non_authorizing"
)

LDAP_HAB_SENIORITY_SCHEMA_MINIMUM = -2147483648
LDAP_HAB_SENIORITY_SCHEMA_MAXIMUM = 2147483647

LDAP_HAB_SENIORITY_EITAS_MINIMUM = 0
LDAP_HAB_SENIORITY_EITAS_MAXIMUM = 2147483647


@dataclass(frozen=True)
class LDAPHabSeniorityPolicy:
    name: str
    value_type: str
    allowed_object_classes: frozenset[str]
    schema_classes: frozenset[str]
    minimum_value: int
    maximum_value: int
    clearable: bool
    duplicate_values_allowed: bool
    higher_values_sort_first: bool
    unset_sort_fallback: str
    property_sets: tuple[str, ...]
    required_roles: frozenset[str]
    public_exposure: bool
    write_authorized: bool
    jobs_enabled: bool
    production_enabled: bool
    status: str
    policy_version: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value_type": self.value_type,
            "allowed_object_classes": sorted(
                self.allowed_object_classes,
                key=str.casefold,
            ),
            "schema_classes": sorted(
                self.schema_classes,
                key=str.casefold,
            ),
            "minimum_value": self.minimum_value,
            "maximum_value": self.maximum_value,
            "clearable": self.clearable,
            "duplicate_values_allowed": (
                self.duplicate_values_allowed
            ),
            "higher_values_sort_first": (
                self.higher_values_sort_first
            ),
            "unset_sort_fallback": (
                self.unset_sort_fallback
            ),
            "property_sets": list(
                self.property_sets
            ),
            "required_roles": sorted(
                self.required_roles,
                key=str.casefold,
            ),
            "public_exposure": self.public_exposure,
            "write_authorized": self.write_authorized,
            "jobs_enabled": self.jobs_enabled,
            "production_enabled": (
                self.production_enabled
            ),
            "status": self.status,
            "policy_version": self.policy_version,
        }


LDAP_HAB_SENIORITY_POLICY = LDAPHabSeniorityPolicy(
    name=LDAP_HAB_SENIORITY_ATTRIBUTE_NAME,
    value_type="integer32",
    allowed_object_classes=frozenset({
        "user",
    }),
    schema_classes=frozenset({
        "organizationalPerson",
    }),
    minimum_value=LDAP_HAB_SENIORITY_EITAS_MINIMUM,
    maximum_value=LDAP_HAB_SENIORITY_EITAS_MAXIMUM,
    clearable=True,
    duplicate_values_allowed=True,
    higher_values_sort_first=True,
    unset_sort_fallback="alphabetical",
    property_sets=(
        "Public Information",
    ),
    required_roles=frozenset({
        "ADAdmin",
        "UltraAdmin",
    }),
    public_exposure=False,
    write_authorized=False,
    jobs_enabled=False,
    production_enabled=False,
    status=LDAP_HAB_SENIORITY_POLICY_STATUS,
    policy_version=LDAP_HAB_SENIORITY_POLICY_VERSION,
)


LDAP_HAB_SENIORITY_SCHEMA_FACTS = MappingProxyType({
    "attribute_syntax": "2.5.5.9",
    "om_syntax": 2,
    "single_valued": True,
    "system_only": False,
    "defunct": False,
    "indexed": True,
    "global_catalog": True,
    "schema_range_lower": None,
    "schema_range_upper": None,
    "property_set": "Public Information",
})


def assert_ldap_hab_seniority_policy_invariants() -> None:
    policy = LDAP_HAB_SENIORITY_POLICY

    if policy.name != "msDS-HABSeniorityIndex":
        raise RuntimeError(
            "Nom HAB Seniority incohérent."
        )

    if policy.value_type != "integer32":
        raise RuntimeError(
            "Le SeniorityIndex doit rester integer32."
        )

    if policy.allowed_object_classes != frozenset({
        "user",
    }):
        raise RuntimeError(
            "La première portée EITAS doit rester user."
        )

    if policy.schema_classes != frozenset({
        "organizationalPerson",
    }):
        raise RuntimeError(
            "Classe de schéma HAB incohérente."
        )

    if (
        policy.minimum_value
        < LDAP_HAB_SENIORITY_SCHEMA_MINIMUM
    ):
        raise RuntimeError(
            "Minimum inférieur à Integer32."
        )

    if (
        policy.maximum_value
        > LDAP_HAB_SENIORITY_SCHEMA_MAXIMUM
    ):
        raise RuntimeError(
            "Maximum supérieur à Integer32."
        )

    if policy.minimum_value < 0:
        raise RuntimeError(
            "La politique EITAS doit rester non négative."
        )

    if (
        policy.maximum_value
        < policy.minimum_value
    ):
        raise RuntimeError(
            "Bornes HAB incohérentes."
        )

    if not policy.clearable:
        raise RuntimeError(
            "Le SeniorityIndex doit pouvoir être effacé."
        )

    if not policy.duplicate_values_allowed:
        raise RuntimeError(
            "Les doublons doivent rester autorisés."
        )

    if not policy.higher_values_sort_first:
        raise RuntimeError(
            "Le tri HAB doit rester décroissant."
        )

    if (
        policy.unset_sort_fallback
        != "alphabetical"
    ):
        raise RuntimeError(
            "Le repli doit rester alphabétique."
        )

    if policy.property_sets != (
        "Public Information",
    ):
        raise RuntimeError(
            "Property set HAB incohérent."
        )

    if policy.required_roles != frozenset({
        "ADAdmin",
        "UltraAdmin",
    }):
        raise RuntimeError(
            "Rôles HAB incohérents."
        )

    if any((
        policy.public_exposure,
        policy.write_authorized,
        policy.jobs_enabled,
        policy.production_enabled,
    )):
        raise RuntimeError(
            "La politique HAB doit rester dormante."
        )


assert_ldap_hab_seniority_policy_invariants()
