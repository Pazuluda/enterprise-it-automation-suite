from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID


ACL_DELEGATION_WRITE_INTENT_CONTRACT_VERSION = (
    "c8.4a1"
)

ACL_DELEGATION_WRITE_INTENT_ACTION = (
    "apply_acl_delegation"
)

ACL_DELEGATION_WRITE_INTENT_EXECUTION_POLICY = (
    "controlled_write_dormant"
)

ACL_DELEGATION_WRITE_INTENT_VALIDATION_ENABLED = True

# C8.4A1 defines a future write contract only.
# Nothing below authorizes job creation, runtime,
# Production execution or Active Directory writes.
ACL_DELEGATION_WRITE_INTENT_JOB_CREATION_ENABLED = False
ACL_DELEGATION_WRITE_INTENT_RUNTIME_ENABLED = False
ACL_DELEGATION_WRITE_INTENT_PRODUCTION_ENABLED = False
ACL_DELEGATION_WRITE_INTENT_AD_WRITE_ENABLED = False


ACL_DELEGATION_WRITE_CONFIRMATION_PHRASE = (
    "APPLY ACL DELEGATION"
)


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


class AclDelegationWriteIntentBadRequest(
    ValueError
):
    pass


@dataclass(frozen=True)
class AclDelegationWriteIntent:
    action: str
    mode: str
    object_dn: str
    principal_identity: str
    access_control_type: str
    rights: tuple[str, ...]
    inheritance_type: str
    object_type_guid: str | None
    inherited_object_type_guid: str | None
    simulation_job_id: str
    security_descriptor_job_id: str
    expected_acl_fingerprint: str
    confirm_object_dn: str
    confirmation_phrase: str
    execution_policy: str
    contract_version: str
    job_creation_authorized: bool
    runtime_authorized: bool
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
        raise AclDelegationWriteIntentBadRequest(
            f"{field_name} contient un caractere "
            "de controle interdit"
        )


def _normalize_dn(
    value,
    field_name: str,
) -> str:
    dn = _clean_string(value)

    if not dn:
        raise AclDelegationWriteIntentBadRequest(
            f"{field_name} est obligatoire"
        )

    _reject_control_characters(
        dn,
        field_name,
    )

    if "=" not in dn or "," not in dn:
        raise AclDelegationWriteIntentBadRequest(
            f"{field_name} doit etre un DN LDAP valide"
        )

    if len(dn) > 2048:
        raise AclDelegationWriteIntentBadRequest(
            f"{field_name} est trop long"
        )

    return dn


def _normalize_principal(value) -> str:
    principal = _clean_string(value)

    if not principal:
        raise AclDelegationWriteIntentBadRequest(
            "principal_identity est obligatoire"
        )

    _reject_control_characters(
        principal,
        "principal_identity",
    )

    if len(principal) > 512:
        raise AclDelegationWriteIntentBadRequest(
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
    except (
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:
        raise AclDelegationWriteIntentBadRequest(
            f"{field_name} doit etre un GUID valide"
        ) from exc

    normalized = str(parsed).lower()

    if (
        normalized
        == "00000000-0000-0000-0000-000000000000"
    ):
        return None

    return normalized


def _normalize_job_id(value) -> str:
    raw = _clean_string(value)

    if not raw:
        raise AclDelegationWriteIntentBadRequest(
            "simulation_job_id est obligatoire"
        )

    try:
        parsed = UUID(raw)
    except (
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:
        raise AclDelegationWriteIntentBadRequest(
            "simulation_job_id doit etre un UUID valide"
        ) from exc

    return str(parsed).lower()


def _normalize_acl_fingerprint(value) -> str:
    fingerprint = _clean_string(value).lower()

    if not fingerprint:
        raise AclDelegationWriteIntentBadRequest(
            "expected_acl_fingerprint est obligatoire"
        )

    if not re.fullmatch(
        r"[0-9a-f]{64}",
        fingerprint,
    ):
        raise AclDelegationWriteIntentBadRequest(
            "expected_acl_fingerprint doit etre "
            "un SHA-256 hexadecimal"
        )

    return fingerprint


def _normalize_rights(value) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise AclDelegationWriteIntentBadRequest(
            "rights doit etre une liste"
        )

    if not value:
        raise AclDelegationWriteIntentBadRequest(
            "Au moins un droit ACL est obligatoire"
        )

    normalized = []

    for raw_right in value:
        right = _clean_string(raw_right)

        if right not in ALLOWED_RIGHTS:
            raise AclDelegationWriteIntentBadRequest(
                "Droit ACL non autorise en C8.4A1 : "
                + right
            )

        if right not in normalized:
            normalized.append(right)

    if len(normalized) > 16:
        raise AclDelegationWriteIntentBadRequest(
            "Trop de droits ACL demandes"
        )

    return tuple(normalized)


def normalize_acl_delegation_write_intent(
    payload: dict,
) -> AclDelegationWriteIntent:
    if not (
        ACL_DELEGATION_WRITE_INTENT_VALIDATION_ENABLED
    ):
        raise AclDelegationWriteIntentBadRequest(
            "Validation ACL write intent desactivee"
        )

    if not isinstance(payload, dict):
        raise AclDelegationWriteIntentBadRequest(
            "Le payload ACL doit etre un objet JSON"
        )

    action = _clean_string(
        payload.get("action")
    )

    if action != ACL_DELEGATION_WRITE_INTENT_ACTION:
        raise AclDelegationWriteIntentBadRequest(
            "Action ACL write intent invalide"
        )

    mode = _clean_string(
        payload.get("mode")
    )

    if mode.lower() != "production":
        raise AclDelegationWriteIntentBadRequest(
            "Une intention d'ecriture ACL doit "
            "explicitement demander Production"
        )

    object_dn = _normalize_dn(
        payload.get("object_dn")
        or payload.get("objectDn")
        or payload.get("dn"),
        "object_dn",
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
        raise AclDelegationWriteIntentBadRequest(
            "C8.4A1 autorise uniquement "
            "les intentions ACE Allow"
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
        raise AclDelegationWriteIntentBadRequest(
            "Portee ACL non autorisee en C8.4A1 : "
            + inheritance_type
        )

    object_type_guid = _normalize_guid(
        payload.get("object_type_guid")
        or payload.get("objectTypeGuid"),
        "object_type_guid",
    )

    inherited_object_type_guid = _normalize_guid(
        payload.get("inherited_object_type_guid")
        or payload.get("inheritedObjectTypeGuid"),
        "inherited_object_type_guid",
    )

    simulation_job_id = _normalize_job_id(
        payload.get("simulation_job_id")
        or payload.get("simulationJobId")
    )

    security_descriptor_job_id = _normalize_job_id(
        payload.get("security_descriptor_job_id")
        or payload.get("securityDescriptorJobId")
    )

    expected_acl_fingerprint = (
        _normalize_acl_fingerprint(
            payload.get("expected_acl_fingerprint")
            or payload.get("expectedAclFingerprint")
        )
    )

    confirm_object_dn = _normalize_dn(
        payload.get("confirm_object_dn")
        or payload.get("confirmObjectDn"),
        "confirm_object_dn",
    )

    if (
        confirm_object_dn.casefold()
        != object_dn.casefold()
    ):
        raise AclDelegationWriteIntentBadRequest(
            "Confirmation DN ACL invalide"
        )

    confirmation_phrase = _clean_string(
        payload.get("confirmation_phrase")
        or payload.get("confirmationPhrase")
    )

    if (
        confirmation_phrase
        != ACL_DELEGATION_WRITE_CONFIRMATION_PHRASE
    ):
        raise AclDelegationWriteIntentBadRequest(
            "Phrase de confirmation ACL invalide"
        )

    return AclDelegationWriteIntent(
        action=action,
        mode="Production",
        object_dn=object_dn,
        principal_identity=principal_identity,
        access_control_type=access_control_type,
        rights=rights,
        inheritance_type=inheritance_type,
        object_type_guid=object_type_guid,
        inherited_object_type_guid=(
            inherited_object_type_guid
        ),
        simulation_job_id=simulation_job_id,
        security_descriptor_job_id=(
            security_descriptor_job_id
        ),
        expected_acl_fingerprint=(
            expected_acl_fingerprint
        ),
        confirm_object_dn=confirm_object_dn,
        confirmation_phrase=confirmation_phrase,
        execution_policy=(
            ACL_DELEGATION_WRITE_INTENT_EXECUTION_POLICY
        ),
        contract_version=(
            ACL_DELEGATION_WRITE_INTENT_CONTRACT_VERSION
        ),
        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,
    )


def assert_acl_delegation_write_intent_invariants(
) -> None:
    if not (
        ACL_DELEGATION_WRITE_INTENT_VALIDATION_ENABLED
    ):
        raise RuntimeError(
            "ACL write intent validation must remain enabled"
        )

    if ACL_DELEGATION_WRITE_INTENT_JOB_CREATION_ENABLED:
        raise RuntimeError(
            "C8.4A1 job creation must remain disabled"
        )

    if ACL_DELEGATION_WRITE_INTENT_RUNTIME_ENABLED:
        raise RuntimeError(
            "C8.4A1 runtime must remain disabled"
        )

    if ACL_DELEGATION_WRITE_INTENT_PRODUCTION_ENABLED:
        raise RuntimeError(
            "C8.4A1 Production must remain disabled"
        )

    if ACL_DELEGATION_WRITE_INTENT_AD_WRITE_ENABLED:
        raise RuntimeError(
            "C8.4A1 AD writes must remain disabled"
        )


assert_acl_delegation_write_intent_invariants()
