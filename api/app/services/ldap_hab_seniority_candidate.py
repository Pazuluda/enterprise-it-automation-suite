from __future__ import annotations

from app.services.ldap_attribute_candidates import (
    C2_FIRST_WAVE_REVIEWED_CANDIDATES,
    LDAPReviewedCandidate,
    get_reviewed_ldap_candidate,
    list_reviewed_ldap_candidates,
)
from app.services.ldap_attribute_policy import (
    resolve_ldap_attribute_policy,
)
from app.services.ldap_hab_seniority_policy import (
    LDAP_HAB_SENIORITY_POLICY,
)


LDAP_HAB_SENIORITY_DORMANT_CANDIDATE = (
    LDAPReviewedCandidate(
        name=LDAP_HAB_SENIORITY_POLICY.name,
        value_type=(
            LDAP_HAB_SENIORITY_POLICY.value_type
        ),
        allowed_object_classes=(
            LDAP_HAB_SENIORITY_POLICY
            .allowed_object_classes
        ),
        minimum_length=0,
        maximum_length=0,
        clearable=(
            LDAP_HAB_SENIORITY_POLICY.clearable
        ),
        property_sets=(
            LDAP_HAB_SENIORITY_POLICY.property_sets
        ),
        required_roles=(
            LDAP_HAB_SENIORITY_POLICY.required_roles
        ),
        minimum_value=(
            LDAP_HAB_SENIORITY_POLICY.minimum_value
        ),
        maximum_value=(
            LDAP_HAB_SENIORITY_POLICY.maximum_value
        ),
        write_authorized=False,
    )
)


def get_ldap_hab_seniority_dormant_metadata() -> dict:
    return {
        "candidate": (
            LDAP_HAB_SENIORITY_DORMANT_CANDIDATE
            .to_dict()
        ),
        "policy": (
            LDAP_HAB_SENIORITY_POLICY.to_dict()
        ),
        "public_registry_member": False,
        "validation_available_by_default": False,
        "frontend_exposed": False,
        "job_creation_enabled": False,
        "production_enabled": False,
    }


def assert_ldap_hab_seniority_candidate_invariants() -> None:
    candidate = (
        LDAP_HAB_SENIORITY_DORMANT_CANDIDATE
    )
    policy = LDAP_HAB_SENIORITY_POLICY

    if candidate.name != policy.name:
        raise RuntimeError(
            "Nom du candidat HAB incohérent."
        )

    if candidate.value_type != "integer32":
        raise RuntimeError(
            "Le candidat HAB doit rester integer32."
        )

    if (
        candidate.allowed_object_classes
        != frozenset({"user"})
    ):
        raise RuntimeError(
            "La portée HAB doit rester user."
        )

    if (
        candidate.minimum_length != 0
        or candidate.maximum_length != 0
    ):
        raise RuntimeError(
            "Un entier HAB ne doit pas avoir de longueurs."
        )

    if (
        candidate.minimum_value
        != policy.minimum_value
    ):
        raise RuntimeError(
            "Minimum HAB incohérent."
        )

    if (
        candidate.maximum_value
        != policy.maximum_value
    ):
        raise RuntimeError(
            "Maximum HAB incohérent."
        )

    if candidate.write_authorized:
        raise RuntimeError(
            "Le candidat HAB ne doit pas autoriser d’écriture."
        )

    if candidate.name in C2_FIRST_WAVE_REVIEWED_CANDIDATES:
        raise RuntimeError(
            "Le candidat HAB ne doit pas être public."
        )

    if get_reviewed_ldap_candidate(candidate.name) is not None:
        raise RuntimeError(
            "Le résolveur public ne doit pas trouver HAB."
        )

    if len(list_reviewed_ldap_candidates()) != 5:
        raise RuntimeError(
            "Le registre public doit rester à cinq attributs."
        )

    current_policy = resolve_ldap_attribute_policy(
        candidate.name
    )

    if not current_policy.denied:
        raise RuntimeError(
            "La politique LDAP HAB doit rester deny."
        )

    if current_policy.generic_ldap_editor_editable:
        raise RuntimeError(
            "HAB ne doit pas être éditable génériquement."
        )


assert_ldap_hab_seniority_candidate_invariants()
