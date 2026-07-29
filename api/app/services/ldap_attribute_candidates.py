from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from app.services.ldap_attribute_policy import (
    C1_VISIBLE_CANONICAL_PROPERTIES,
    LDAP_ATTRIBUTE_POLICY_DEFAULT,
    LDAP_GENERIC_EDITOR_WRITES_ENABLED,
    LDAP_SCHEMA_CATALOG_IS_AUTHORIZATION,
    resolve_ldap_attribute_policy,
)


LDAP_REVIEWED_CANDIDATE_POLICY_VERSION = "c2.3a.1"
LDAP_REVIEWED_CANDIDATE_STATUS = "reviewed_candidate_non_authorizing"
LDAP_REVIEWED_CANDIDATES_AUTHORIZE_WRITES = False


@dataclass(frozen=True)
class LDAPReviewedCandidate:
    name: str
    value_type: str
    allowed_object_classes: frozenset[str]
    minimum_length: int
    maximum_length: int
    clearable: bool
    property_sets: tuple[str, ...]
    required_roles: frozenset[str]
    write_authorized: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value_type": self.value_type,
            "allowed_object_classes": sorted(
                self.allowed_object_classes,
                key=str.casefold,
            ),
            "minimum_length": self.minimum_length,
            "maximum_length": self.maximum_length,
            "clearable": self.clearable,
            "property_sets": list(self.property_sets),
            "required_roles": sorted(
                self.required_roles,
                key=str.casefold,
            ),
            "write_authorized": self.write_authorized,
            "status": LDAP_REVIEWED_CANDIDATE_STATUS,
        }


_REQUIRED_ROLES = frozenset({"ADAdmin", "UltraAdmin"})


C2_FIRST_WAVE_REVIEWED_CANDIDATES = MappingProxyType(
    {
        "employeeType": LDAPReviewedCandidate(
            name="employeeType",
            value_type="single_text",
            allowed_object_classes=frozenset({"user"}),
            minimum_length=1,
            maximum_length=256,
            clearable=True,
            property_sets=(),
            required_roles=_REQUIRED_ROLES,
        ),
        "preferredLanguage": LDAPReviewedCandidate(
            name="preferredLanguage",
            value_type="single_text",
            allowed_object_classes=frozenset({"user"}),
            minimum_length=0,
            maximum_length=64,
            clearable=True,
            property_sets=(),
            required_roles=_REQUIRED_ROLES,
        ),
        "personalTitle": LDAPReviewedCandidate(
            name="personalTitle",
            value_type="single_text",
            allowed_object_classes=frozenset({"user", "contact"}),
            minimum_length=1,
            maximum_length=64,
            clearable=True,
            property_sets=("Personal Information",),
            required_roles=_REQUIRED_ROLES,
        ),
        "middleName": LDAPReviewedCandidate(
            name="middleName",
            value_type="single_text",
            allowed_object_classes=frozenset({"user", "contact"}),
            minimum_length=0,
            maximum_length=64,
            clearable=True,
            property_sets=(),
            required_roles=_REQUIRED_ROLES,
        ),
        "comment": LDAPReviewedCandidate(
            name="comment",
            value_type="single_text",
            allowed_object_classes=frozenset({"user", "contact"}),
            minimum_length=0,
            maximum_length=1024,
            clearable=True,
            property_sets=("General Information",),
            required_roles=_REQUIRED_ROLES,
        ),
    }
)


_CANDIDATE_INDEX = MappingProxyType(
    {
        name.casefold(): candidate
        for name, candidate in C2_FIRST_WAVE_REVIEWED_CANDIDATES.items()
    }
)


def get_reviewed_ldap_candidate(
    attribute_name: object,
) -> LDAPReviewedCandidate | None:
    if not isinstance(attribute_name, str):
        return None

    normalized = attribute_name.strip()

    if not normalized:
        return None

    return _CANDIDATE_INDEX.get(normalized.casefold())


def list_reviewed_ldap_candidates() -> list[dict]:
    return [
        candidate.to_dict()
        for candidate in sorted(
            C2_FIRST_WAVE_REVIEWED_CANDIDATES.values(),
            key=lambda item: item.name.casefold(),
        )
    ]


def assert_reviewed_candidate_invariants() -> None:
    expected_names = {
        "employeeType",
        "preferredLanguage",
        "personalTitle",
        "middleName",
        "comment",
    }

    if set(C2_FIRST_WAVE_REVIEWED_CANDIDATES) != expected_names:
        raise RuntimeError(
            "La premiere vague LDAP controlee doit contenir cinq attributs."
        )

    if LDAP_REVIEWED_CANDIDATE_STATUS != "reviewed_candidate_non_authorizing":
        raise RuntimeError(
            "Le registre des candidats doit rester non autorisant."
        )

    if LDAP_REVIEWED_CANDIDATES_AUTHORIZE_WRITES:
        raise RuntimeError(
            "Le registre des candidats ne doit jamais autoriser une ecriture."
        )

    if LDAP_ATTRIBUTE_POLICY_DEFAULT != "deny":
        raise RuntimeError(
            "La politique LDAP par defaut doit rester deny."
        )

    if LDAP_SCHEMA_CATALOG_IS_AUTHORIZATION:
        raise RuntimeError(
            "Le catalogue LDAP ne peut pas devenir une autorisation."
        )

    if LDAP_GENERIC_EDITOR_WRITES_ENABLED:
        raise RuntimeError(
            "Les ecritures LDAP generiques doivent rester desactivees."
        )

    for name, candidate in C2_FIRST_WAVE_REVIEWED_CANDIDATES.items():
        if candidate.name != name:
            raise RuntimeError(
                f"Nom de candidat incoherent: {name!r}."
            )

        if candidate.write_authorized:
            raise RuntimeError(
                f"Le candidat {name!r} autorise une ecriture."
            )

        if candidate.required_roles != _REQUIRED_ROLES:
            raise RuntimeError(
                f"Roles incoherents pour {name!r}."
            )

        if candidate.value_type != "single_text":
            raise RuntimeError(
                f"Type non controle pour {name!r}."
            )

        if candidate.minimum_length < 0:
            raise RuntimeError(
                f"Longueur minimale negative pour {name!r}."
            )

        if candidate.maximum_length < candidate.minimum_length:
            raise RuntimeError(
                f"Bornes incoherentes pour {name!r}."
            )

        if name in C1_VISIBLE_CANONICAL_PROPERTIES:
            raise RuntimeError(
                f"Le candidat {name!r} chevauche la politique C1."
            )

        current_policy = resolve_ldap_attribute_policy(name)

        if not current_policy.denied:
            raise RuntimeError(
                f"Le candidat {name!r} ne doit pas encore etre visible."
            )

        if current_policy.generic_ldap_editor_editable:
            raise RuntimeError(
                f"Le candidat {name!r} ne doit pas etre modifiable."
            )


assert_reviewed_candidate_invariants()
