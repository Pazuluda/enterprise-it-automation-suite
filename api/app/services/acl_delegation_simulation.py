from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


ACL_DELEGATION_SIMULATION_CONTRACT_VERSION = (
    "c8.3a1"
)

ACL_DELEGATION_SIMULATION_ACTION = (
    "simulate_acl_delegation"
)

ACL_DELEGATION_SIMULATION_EXECUTION_POLICY = (
    "simulation_only"
)

ACL_DELEGATION_SIMULATION_VALIDATION_ENABLED = True

# C8.3A1 is intentionally dormant.
ACL_DELEGATION_SIMULATION_JOB_CREATION_ENABLED = True
ACL_DELEGATION_SIMULATION_PRODUCTION_ENABLED = False
ACL_DELEGATION_SIMULATION_AD_WRITE_ENABLED = False


ALLOWED_ACCESS_CONTROL_TYPES = frozenset({
    "Allow",
})

ALLOWED_RIGHTS = frozenset({
    "ReadProperty",
    "WriteProperty",
    "CreateChild",
    "DeleteChild",
    "ListChildren",
    "ReadControl",
    "ExtendedRight",
    "GenericRead",
})

ALLOWED_INHERITANCE_TYPES = frozenset({
    "None",
    "All",
    "Descendents",
    "SelfAndChildren",
    "Children",
})


class AclDelegationSimulationBadRequest(
    ValueError
):
    pass


@dataclass(frozen=True)
class AclDelegationSimulationRequest:
    action: str
    mode: str
    object_dn: str
    principal_identity: str
    access_control_type: str
    rights: tuple[str, ...]
    inheritance_type: str
    object_type_guid: str | None
    inherited_object_type_guid: str | None
    execution_policy: str
    contract_version: str
    simulation_validation_authorized: bool
    simulation_job_authorized: bool
    production_authorized: bool
    ad_write_authorized: bool


def _clean_string(value) -> str:
    return str(value or "").strip()


def _reject_control_characters(
    value: str,
    field_name: str,
) -> None:
    if any(
        ord(character) < 32
        for character in value
    ):
        raise AclDelegationSimulationBadRequest(
            f"{field_name} contient un caractere "
            "de controle interdit"
        )


def _normalize_dn(value) -> str:
    dn = _clean_string(value)

    if not dn:
        raise AclDelegationSimulationBadRequest(
            "object_dn est obligatoire"
        )

    _reject_control_characters(
        dn,
        "object_dn",
    )

    if "=" not in dn or "," not in dn:
        raise AclDelegationSimulationBadRequest(
            "object_dn doit etre un DN LDAP valide"
        )

    if len(dn) > 2048:
        raise AclDelegationSimulationBadRequest(
            "object_dn est trop long"
        )

    return dn


def _normalize_principal(value) -> str:
    principal = _clean_string(value)

    if not principal:
        raise AclDelegationSimulationBadRequest(
            "principal_identity est obligatoire"
        )

    _reject_control_characters(
        principal,
        "principal_identity",
    )

    if len(principal) > 512:
        raise AclDelegationSimulationBadRequest(
            "principal_identity est trop long"
        )

    return principal


def _normalize_guid(
    value,
    field_name: str,
) -> str | None:
    raw = _clean_string(value)

    if not raw:
        return None

    try:
        parsed = UUID(raw)
    except (ValueError, TypeError, AttributeError):
        raise AclDelegationSimulationBadRequest(
            f"{field_name} doit etre un GUID valide"
        )

    normalized = str(parsed).lower()

    if (
        normalized
        == "00000000-0000-0000-0000-000000000000"
    ):
        return None

    return normalized


def _normalize_rights(value) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise AclDelegationSimulationBadRequest(
            "rights doit etre une liste"
        )

    if not value:
        raise AclDelegationSimulationBadRequest(
            "Au moins un droit ACL est obligatoire"
        )

    normalized = []

    for raw_right in value:
        right = _clean_string(raw_right)

        if right not in ALLOWED_RIGHTS:
            raise AclDelegationSimulationBadRequest(
                "Droit ACL non autorise en C8.3A1 : "
                + right
            )

        if right not in normalized:
            normalized.append(right)

    if len(normalized) > 16:
        raise AclDelegationSimulationBadRequest(
            "Trop de droits ACL demandes"
        )

    return tuple(normalized)


def normalize_acl_delegation_simulation_request(
    payload: dict,
) -> AclDelegationSimulationRequest:
    if not ACL_DELEGATION_SIMULATION_VALIDATION_ENABLED:
        raise AclDelegationSimulationBadRequest(
            "La validation ACL Simulation est desactivee"
        )

    if not isinstance(payload, dict):
        raise AclDelegationSimulationBadRequest(
            "Le payload ACL doit etre un objet JSON"
        )

    action = _clean_string(
        payload.get("action")
    )

    if action != ACL_DELEGATION_SIMULATION_ACTION:
        raise AclDelegationSimulationBadRequest(
            "Action ACL Simulation invalide"
        )

    mode = _clean_string(
        payload.get("mode")
        or "Simulation"
    )

    if mode.lower() != "simulation":
        raise AclDelegationSimulationBadRequest(
            "La delegation ACL est disponible "
            "uniquement en mode Simulation"
        )

    object_dn = _normalize_dn(
        payload.get("object_dn")
        or payload.get("objectDn")
        or payload.get("dn")
    )

    principal_identity = _normalize_principal(
        payload.get("principal_identity")
        or payload.get("principalIdentity")
        or payload.get("principal")
    )

    access_control_type = _clean_string(
        payload.get("access_control_type")
        or payload.get("accessControlType")
        or "Allow"
    )

    if (
        access_control_type
        not in ALLOWED_ACCESS_CONTROL_TYPES
    ):
        raise AclDelegationSimulationBadRequest(
            "C8.3A1 autorise uniquement "
            "les ACE Allow"
        )

    rights = _normalize_rights(
        payload.get("rights")
    )

    inheritance_type = _clean_string(
        payload.get("inheritance_type")
        or payload.get("inheritanceType")
        or "None"
    )

    if (
        inheritance_type
        not in ALLOWED_INHERITANCE_TYPES
    ):
        raise AclDelegationSimulationBadRequest(
            "Portee d'heritage ACL non autorisee"
        )

    object_type_guid = _normalize_guid(
        payload.get("object_type_guid")
        or payload.get("objectTypeGuid"),
        "object_type_guid",
    )

    inherited_object_type_guid = _normalize_guid(
        payload.get(
            "inherited_object_type_guid"
        )
        or payload.get(
            "inheritedObjectTypeGuid"
        ),
        "inherited_object_type_guid",
    )

    request = AclDelegationSimulationRequest(
        action=ACL_DELEGATION_SIMULATION_ACTION,
        mode="Simulation",
        object_dn=object_dn,
        principal_identity=principal_identity,
        access_control_type=access_control_type,
        rights=rights,
        inheritance_type=inheritance_type,
        object_type_guid=object_type_guid,
        inherited_object_type_guid=(
            inherited_object_type_guid
        ),
        execution_policy=(
            ACL_DELEGATION_SIMULATION_EXECUTION_POLICY
        ),
        contract_version=(
            ACL_DELEGATION_SIMULATION_CONTRACT_VERSION
        ),
        simulation_validation_authorized=True,
        simulation_job_authorized=True,
        production_authorized=False,
        ad_write_authorized=False,
    )

    return request


def assert_acl_delegation_simulation_invariants() -> None:
    if not ACL_DELEGATION_SIMULATION_VALIDATION_ENABLED:
        raise RuntimeError(
            "ACL Simulation validation must remain enabled"
        )

    if not ACL_DELEGATION_SIMULATION_JOB_CREATION_ENABLED:
        raise RuntimeError(
            "ACL Simulation job creation must remain enabled"
        )

    if ACL_DELEGATION_SIMULATION_PRODUCTION_ENABLED:
        raise RuntimeError(
            "C8.3A1 Production must remain disabled"
        )

    if ACL_DELEGATION_SIMULATION_AD_WRITE_ENABLED:
        raise RuntimeError(
            "C8.3A1 AD write must remain disabled"
        )

    sample = normalize_acl_delegation_simulation_request({
        "action": (
            ACL_DELEGATION_SIMULATION_ACTION
        ),
        "mode": "Simulation",
        "object_dn": (
            "OU=test,OU=Users,OU=EITAS,"
            "DC=API,DC=LOCAL"
        ),
        "principal_identity": (
            "API\\GG_IT_Admin"
        ),
        "access_control_type": "Allow",
        "rights": [
            "ReadProperty",
        ],
        "inheritance_type": "None",
    })

    if not sample.simulation_job_authorized:
        raise RuntimeError(
            "ACL Simulation must authorize Simulation jobs"
        )

    if sample.production_authorized:
        raise RuntimeError(
            "C8.3A1 must not authorize Production"
        )

    if sample.ad_write_authorized:
        raise RuntimeError(
            "C8.3A1 must not authorize AD writes"
        )


assert_acl_delegation_simulation_invariants()
