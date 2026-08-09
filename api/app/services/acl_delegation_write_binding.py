from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.services.acl_delegation_write_intent import (
    AclDelegationWriteIntent,
    AclDelegationWriteIntentBadRequest,
    normalize_acl_delegation_write_intent,
)


ACL_DELEGATION_WRITE_BINDING_CONTRACT_VERSION = (
    "c8.4a2"
)

ACL_DELEGATION_WRITE_BINDING_ENABLED = True

# C8.4A2 validates evidence only.
# It must not expose an executable AD write path.
ACL_DELEGATION_WRITE_BINDING_JOB_CREATION_ENABLED = False
ACL_DELEGATION_WRITE_BINDING_RUNTIME_ENABLED = False
ACL_DELEGATION_WRITE_BINDING_PRODUCTION_ENABLED = False
ACL_DELEGATION_WRITE_BINDING_AD_WRITE_ENABLED = False


ZERO_GUID = (
    "00000000-0000-0000-0000-000000000000"
)

ACL_DELEGATION_DACL_FINGERPRINT_VERSION = (
    "sddl-access-sha256-v1"
)

ACL_DELEGATION_ACL_STATE_FINGERPRINT_VERSION = (
    "eitas-acl-state-v2"
)


class AclDelegationWriteBindingBadRequest(
    ValueError
):
    pass


@dataclass(frozen=True)
class AclDelegationWriteBinding:
    intent: AclDelegationWriteIntent
    simulation_job_id: str
    security_descriptor_job_id: str
    target_dn: str
    target_object_guid: str
    principal_dn: str
    principal_sid: str
    dacl_sddl_sha256: str
    acl_fingerprint: str
    acl_rule_count: int
    contract_version: str
    binding_validated: bool
    job_creation_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    ad_write_authorized: bool


def _clean_string(value) -> str:
    return str(value or "").strip()


def _normalize_uuid(value, field_name: str) -> str:
    raw = _clean_string(value)

    try:
        parsed = UUID(raw)
    except (
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:
        raise AclDelegationWriteBindingBadRequest(
            f"{field_name} invalide"
        ) from exc

    return str(parsed).lower()


def _normalize_guid(value) -> str:
    raw = _clean_string(value)

    if not raw:
        return ZERO_GUID

    try:
        return str(UUID(raw)).lower()
    except (
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:
        raise AclDelegationWriteBindingBadRequest(
            "GUID ACL invalide dans le descripteur"
        ) from exc


def _normalize_sha256(
    value,
    field_name: str,
) -> str:
    raw = _clean_string(value).lower()

    if len(raw) != 64:
        raise AclDelegationWriteBindingBadRequest(
            f"{field_name} doit etre un SHA-256 hexadecimal"
        )

    try:
        int(raw, 16)
    except ValueError as exc:
        raise AclDelegationWriteBindingBadRequest(
            f"{field_name} doit etre un SHA-256 hexadecimal"
        ) from exc

    return raw


def _normalize_rights_string(value) -> tuple[str, ...]:
    raw = _clean_string(value)

    if not raw:
        raise AclDelegationWriteBindingBadRequest(
            "Droits ACL absents du descripteur"
        )

    rights = {
        part.strip()
        for part in raw.split(",")
        if part.strip()
    }

    if not rights:
        raise AclDelegationWriteBindingBadRequest(
            "Droits ACL vides dans le descripteur"
        )

    return tuple(
        sorted(
            rights,
            key=str.casefold,
        )
    )


def _canonical_acl_rule(rule: dict) -> dict:
    if not isinstance(rule, dict):
        raise AclDelegationWriteBindingBadRequest(
            "Regle DACL invalide"
        )

    sid = _clean_string(
        rule.get("sid")
    )

    if not sid:
        raise AclDelegationWriteBindingBadRequest(
            "SID absent d'une regle DACL"
        )

    access_control_type = _clean_string(
        rule.get("access_control_type")
    )

    if access_control_type not in {
        "Allow",
        "Deny",
    }:
        raise AclDelegationWriteBindingBadRequest(
            "Type ACE invalide dans la DACL"
        )

    inheritance_type = _clean_string(
        rule.get("inheritance_type")
    )

    inheritance_flags = _clean_string(
        rule.get("inheritance_flags")
    )

    propagation_flags = _clean_string(
        rule.get("propagation_flags")
    )

    if not inheritance_type:
        raise AclDelegationWriteBindingBadRequest(
            "inheritance_type absent de la DACL"
        )

    if not inheritance_flags:
        raise AclDelegationWriteBindingBadRequest(
            "inheritance_flags absent de la DACL"
        )

    if not propagation_flags:
        raise AclDelegationWriteBindingBadRequest(
            "propagation_flags absent de la DACL"
        )

    is_inherited = rule.get("is_inherited")

    if not isinstance(is_inherited, bool):
        raise AclDelegationWriteBindingBadRequest(
            "is_inherited invalide dans la DACL"
        )

    return {
        "sid": sid.upper(),
        "access_control_type": (
            access_control_type
        ),
        "rights": list(
            _normalize_rights_string(
                rule.get(
                    "active_directory_rights"
                )
            )
        ),
        "inheritance_type": (
            inheritance_type
        ),
        "inheritance_flags": (
            inheritance_flags
        ),
        "propagation_flags": (
            propagation_flags
        ),
        "is_inherited": is_inherited,
        "object_type_guid": _normalize_guid(
            rule.get("object_type_guid")
        ),
        "inherited_object_type_guid": (
            _normalize_guid(
                rule.get(
                    "inherited_object_type_guid"
                )
            )
        ),
    }


def canonicalize_acl_descriptor(
    descriptor: dict,
) -> dict:
    if not isinstance(descriptor, dict):
        raise AclDelegationWriteBindingBadRequest(
            "Descripteur ACL invalide"
        )

    if descriptor.get("read_only") is not True:
        raise AclDelegationWriteBindingBadRequest(
            "Le descripteur ACL doit provenir "
            "d'une lecture read-only"
        )

    if descriptor.get("sacl_included") is not False:
        raise AclDelegationWriteBindingBadRequest(
            "La SACL doit rester exclue"
        )

    inheritance_enabled = descriptor.get(
        "inheritance_enabled"
    )

    access_rules_protected = descriptor.get(
        "access_rules_protected"
    )

    if not isinstance(
        inheritance_enabled,
        bool,
    ):
        raise AclDelegationWriteBindingBadRequest(
            "inheritance_enabled invalide"
        )

    if not isinstance(
        access_rules_protected,
        bool,
    ):
        raise AclDelegationWriteBindingBadRequest(
            "access_rules_protected invalide"
        )

    rules = descriptor.get("rules")

    if not isinstance(rules, list):
        raise AclDelegationWriteBindingBadRequest(
            "rules doit etre une liste"
        )

    canonical_rules = [
        _canonical_acl_rule(rule)
        for rule in rules
    ]

    canonical_rules.sort(
        key=lambda rule: json.dumps(
            rule,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
    )

    return {
        "inheritance_enabled": (
            inheritance_enabled
        ),
        "access_rules_protected": (
            access_rules_protected
        ),
        "rules": canonical_rules,
    }


def calculate_acl_fingerprint(
    descriptor: dict,
) -> str:
    canonical = canonicalize_acl_descriptor(
        descriptor
    )

    object_guid = _normalize_uuid(
        descriptor.get("object_guid"),
        "security_descriptor.object_guid",
    )

    dacl_fingerprint_version = _clean_string(
        descriptor.get(
            "dacl_fingerprint_version"
        )
    )

    if (
        dacl_fingerprint_version
        != ACL_DELEGATION_DACL_FINGERPRINT_VERSION
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Version du fingerprint DACL invalide"
        )

    dacl_sddl_sha256 = _normalize_sha256(
        descriptor.get("dacl_sddl_sha256"),
        "security_descriptor.dacl_sddl_sha256",
    )

    material = {
        "fingerprint_version": (
            ACL_DELEGATION_ACL_STATE_FINGERPRINT_VERSION
        ),
        "object_guid": object_guid,
        "dacl_fingerprint_version": (
            dacl_fingerprint_version
        ),
        "dacl_sddl_sha256": (
            dacl_sddl_sha256
        ),
        "semantic_dacl": canonical,
    }

    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def _extract_security_descriptor(
    job: dict,
) -> dict:
    result = job.get("result")

    if isinstance(result, dict):
        return result

    output = job.get("output")

    if isinstance(output, dict):
        return output

    raise AclDelegationWriteBindingBadRequest(
        "Resultat Security Descriptor absent"
    )


def _parse_timestamp(
    value,
    field_name: str,
) -> datetime:
    raw = _clean_string(value)

    if not raw:
        raise AclDelegationWriteBindingBadRequest(
            f"{field_name} absent"
        )

    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise AclDelegationWriteBindingBadRequest(
            f"{field_name} invalide"
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(timezone.utc)


def _normalize_optional_guid(value) -> str | None:
    raw = _clean_string(value)

    if not raw:
        return None

    normalized = _normalize_guid(raw)

    if normalized == ZERO_GUID:
        return None

    return normalized


def _normalized_rights_list(value) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise AclDelegationWriteBindingBadRequest(
            "Liste de droits de Simulation invalide"
        )

    normalized = {
        _clean_string(item)
        for item in value
        if _clean_string(item)
    }

    return tuple(
        sorted(
            normalized,
            key=str.casefold,
        )
    )


def validate_acl_delegation_write_binding(
    intent_payload: dict,
    simulation_job: dict,
    security_descriptor_job: dict,
) -> AclDelegationWriteBinding:
    if not ACL_DELEGATION_WRITE_BINDING_ENABLED:
        raise AclDelegationWriteBindingBadRequest(
            "Validation du binding ACL desactivee"
        )

    try:
        intent = normalize_acl_delegation_write_intent(
            intent_payload
        )
    except AclDelegationWriteIntentBadRequest as exc:
        raise AclDelegationWriteBindingBadRequest(
            str(exc)
        ) from exc

    if not isinstance(simulation_job, dict):
        raise AclDelegationWriteBindingBadRequest(
            "Job de Simulation ACL invalide"
        )

    simulation_job_id = _normalize_uuid(
        simulation_job.get("id"),
        "simulation_job.id",
    )

    if simulation_job_id != intent.simulation_job_id:
        raise AclDelegationWriteBindingBadRequest(
            "Le job de Simulation ne correspond pas "
            "a l'intention ACL"
        )

    if (
        simulation_job.get("action")
        != "simulate_acl_delegation"
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Action du job de Simulation invalide"
        )

    if simulation_job.get("status") != "completed":
        raise AclDelegationWriteBindingBadRequest(
            "Le job de Simulation n'est pas termine"
        )

    if simulation_job.get("success") is not True:
        raise AclDelegationWriteBindingBadRequest(
            "Le job de Simulation n'a pas reussi"
        )

    simulation_payload = simulation_job.get(
        "payload"
    )

    simulation_output = simulation_job.get(
        "output"
    )

    if not isinstance(simulation_payload, dict):
        raise AclDelegationWriteBindingBadRequest(
            "Payload de Simulation absent"
        )

    if not isinstance(simulation_output, dict):
        raise AclDelegationWriteBindingBadRequest(
            "Output de Simulation absent"
        )

    expected_invariants = {
        "action": "simulate_acl_delegation",
        "mode": "Simulation",
        "simulated": True,
        "write_performed": False,
        "production_authorized": False,
        "ad_write_authorized": False,
        "execution_policy": "simulation_only",
    }

    for key, expected in expected_invariants.items():
        if simulation_output.get(key) != expected:
            raise AclDelegationWriteBindingBadRequest(
                "Invariant C8.3 invalide : "
                + key
            )

    if (
        _clean_string(
            simulation_payload.get("object_dn")
        ).casefold()
        != intent.object_dn.casefold()
    ):
        raise AclDelegationWriteBindingBadRequest(
            "La cible differe de la Simulation"
        )

    if (
        _clean_string(
            simulation_payload.get(
                "principal_identity"
            )
        ).casefold()
        != intent.principal_identity.casefold()
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Le principal differe de la Simulation"
        )

    if (
        simulation_payload.get(
            "access_control_type"
        )
        != intent.access_control_type
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Le type ACE differe de la Simulation"
        )

    if (
        _normalized_rights_list(
            simulation_payload.get("rights")
        )
        != _normalized_rights_list(intent.rights)
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Les droits different de la Simulation"
        )

    if (
        simulation_payload.get(
            "inheritance_type"
        )
        != intent.inheritance_type
    ):
        raise AclDelegationWriteBindingBadRequest(
            "La portee differe de la Simulation"
        )

    if (
        _normalize_optional_guid(
            simulation_payload.get(
                "object_type_guid"
            )
        )
        != intent.object_type_guid
    ):
        raise AclDelegationWriteBindingBadRequest(
            "object_type_guid differe "
            "de la Simulation"
        )

    if (
        _normalize_optional_guid(
            simulation_payload.get(
                "inherited_object_type_guid"
            )
        )
        != intent.inherited_object_type_guid
    ):
        raise AclDelegationWriteBindingBadRequest(
            "inherited_object_type_guid differe "
            "de la Simulation"
        )

    target = simulation_output.get("target")
    principal = simulation_output.get("principal")
    ace = simulation_output.get("ace")

    if not isinstance(target, dict):
        raise AclDelegationWriteBindingBadRequest(
            "Cible resolue absente de la Simulation"
        )

    if not isinstance(principal, dict):
        raise AclDelegationWriteBindingBadRequest(
            "Principal resolu absent de la Simulation"
        )

    if not isinstance(ace, dict):
        raise AclDelegationWriteBindingBadRequest(
            "ACE resolue absente de la Simulation"
        )

    target_dn = _clean_string(
        target.get("dn")
    )

    if target_dn.casefold() != intent.object_dn.casefold():
        raise AclDelegationWriteBindingBadRequest(
            "La cible resolue ne correspond pas"
        )

    simulation_target_object_guid = _normalize_uuid(
        target.get("object_guid"),
        "simulation.target.object_guid",
    )

    principal_dn = _clean_string(
        principal.get("dn")
    )

    principal_sid = _clean_string(
        principal.get("sid")
    )

    if not principal_dn or not principal_sid:
        raise AclDelegationWriteBindingBadRequest(
            "Identite resolue du principal incomplete"
        )

    if ace.get(
        "access_control_type"
    ) != intent.access_control_type:
        raise AclDelegationWriteBindingBadRequest(
            "ACE resolue incompatible"
        )

    if (
        _normalized_rights_list(
            ace.get("rights")
        )
        != _normalized_rights_list(intent.rights)
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Droits resolus incompatibles"
        )

    if (
        ace.get("inheritance_type")
        != intent.inheritance_type
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Portee resolue incompatible"
        )

    if (
        _normalize_optional_guid(
            ace.get("object_type_guid")
        )
        != intent.object_type_guid
    ):
        raise AclDelegationWriteBindingBadRequest(
            "GUID objet resolu incompatible"
        )

    if (
        _normalize_optional_guid(
            ace.get(
                "inherited_object_type_guid"
            )
        )
        != intent.inherited_object_type_guid
    ):
        raise AclDelegationWriteBindingBadRequest(
            "GUID herite resolu incompatible"
        )

    if not isinstance(
        security_descriptor_job,
        dict,
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Job Security Descriptor invalide"
        )

    security_job_id = _normalize_uuid(
        security_descriptor_job.get("id"),
        "security_descriptor_job.id",
    )

    if (
        security_job_id
        != intent.security_descriptor_job_id
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Le job Security Descriptor ne correspond "
            "pas a l'intention ACL"
        )

    if (
        security_descriptor_job.get("action")
        != "get_security_descriptor"
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Action Security Descriptor invalide"
        )

    if (
        security_descriptor_job.get("status")
        != "completed"
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Le job Security Descriptor "
            "n'est pas termine"
        )

    if (
        security_descriptor_job.get("success")
        is not True
    ):
        raise AclDelegationWriteBindingBadRequest(
            "La lecture Security Descriptor "
            "n'a pas reussi"
        )

    descriptor = _extract_security_descriptor(
        security_descriptor_job
    )

    if (
        descriptor.get("action")
        != "get_security_descriptor"
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Resultat Security Descriptor invalide"
        )

    descriptor_dn = _clean_string(
        descriptor.get("object_dn")
    )

    if (
        descriptor_dn.casefold()
        != intent.object_dn.casefold()
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Le Security Descriptor concerne "
            "une autre cible"
        )

    target_object_guid = _normalize_uuid(
        descriptor.get("object_guid"),
        "security_descriptor.object_guid",
    )

    if (
        target_object_guid
        != simulation_target_object_guid
    ):
        raise AclDelegationWriteBindingBadRequest(
            "L'objectGUID de la cible a change "
            "entre la Simulation et la lecture DACL"
        )

    dacl_fingerprint_version = _clean_string(
        descriptor.get(
            "dacl_fingerprint_version"
        )
    )

    if (
        dacl_fingerprint_version
        != ACL_DELEGATION_DACL_FINGERPRINT_VERSION
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Version du fingerprint DACL invalide"
        )

    dacl_sddl_sha256 = _normalize_sha256(
        descriptor.get("dacl_sddl_sha256"),
        "security_descriptor.dacl_sddl_sha256",
    )

    simulation_completed_at = _parse_timestamp(
        simulation_job.get("completed_at"),
        "simulation.completed_at",
    )

    security_completed_at = _parse_timestamp(
        security_descriptor_job.get(
            "completed_at"
        ),
        "security_descriptor.completed_at",
    )

    if security_completed_at < simulation_completed_at:
        raise AclDelegationWriteBindingBadRequest(
            "Le Security Descriptor doit etre lu "
            "apres la Simulation"
        )

    fingerprint = calculate_acl_fingerprint(
        descriptor
    )

    if (
        fingerprint
        != intent.expected_acl_fingerprint
    ):
        raise AclDelegationWriteBindingBadRequest(
            "Fingerprint DACL obsolete ou invalide"
        )

    rules = descriptor.get("rules")

    return AclDelegationWriteBinding(
        intent=intent,
        simulation_job_id=simulation_job_id,
        security_descriptor_job_id=(
            security_job_id
        ),
        target_dn=target_dn,
        target_object_guid=target_object_guid,
        principal_dn=principal_dn,
        principal_sid=principal_sid,
        dacl_sddl_sha256=dacl_sddl_sha256,
        acl_fingerprint=fingerprint,
        acl_rule_count=len(rules),
        contract_version=(
            ACL_DELEGATION_WRITE_BINDING_CONTRACT_VERSION
        ),
        binding_validated=True,
        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,
    )


def assert_acl_delegation_write_binding_invariants(
) -> None:
    if not ACL_DELEGATION_WRITE_BINDING_ENABLED:
        raise RuntimeError(
            "ACL write binding validation "
            "must remain enabled"
        )

    if (
        ACL_DELEGATION_WRITE_BINDING_JOB_CREATION_ENABLED
    ):
        raise RuntimeError(
            "C8.4A2 job creation must remain disabled"
        )

    if ACL_DELEGATION_WRITE_BINDING_RUNTIME_ENABLED:
        raise RuntimeError(
            "C8.4A2 runtime must remain disabled"
        )

    if (
        ACL_DELEGATION_WRITE_BINDING_PRODUCTION_ENABLED
    ):
        raise RuntimeError(
            "C8.4A2 Production must remain disabled"
        )

    if ACL_DELEGATION_WRITE_BINDING_AD_WRITE_ENABLED:
        raise RuntimeError(
            "C8.4A2 AD writes must remain disabled"
        )


assert_acl_delegation_write_binding_invariants()
