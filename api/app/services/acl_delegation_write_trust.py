from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.storage import load_json
from app.services.acl_delegation_write_binding import (
    AclDelegationWriteBinding,
    AclDelegationWriteBindingBadRequest,
    validate_acl_delegation_write_binding,
)
from app.services.acl_delegation_write_intent import (
    AclDelegationWriteIntent,
    AclDelegationWriteIntentBadRequest,
    normalize_acl_delegation_write_intent,
)


ACL_DELEGATION_WRITE_TRUST_CONTRACT_VERSION = "c8.4b1"

ACL_DELEGATION_WRITE_TRUST_ENABLED = True

# C8.4B1 resolves and validates trusted server evidence only.
# It MUST NOT create or execute an ACL write job.
ACL_DELEGATION_WRITE_TRUST_JOB_CREATION_ENABLED = False
ACL_DELEGATION_WRITE_TRUST_RUNTIME_ENABLED = False
ACL_DELEGATION_WRITE_TRUST_PRODUCTION_ENABLED = False
ACL_DELEGATION_WRITE_TRUST_AD_WRITE_ENABLED = False

# Strong freshness windows.
ACL_DELEGATION_WRITE_MAX_SIMULATION_AGE_SECONDS = 900
ACL_DELEGATION_WRITE_MAX_DESCRIPTOR_AGE_SECONDS = 120
ACL_DELEGATION_WRITE_MAX_CLOCK_SKEW_SECONDS = 30


CANONICAL_INTENT_KEYS = frozenset({
    "action",
    "mode",
    "object_dn",
    "principal_identity",
    "access_control_type",
    "rights",
    "inheritance_type",
    "object_type_guid",
    "inherited_object_type_guid",
    "simulation_job_id",
    "security_descriptor_job_id",
    "expected_acl_fingerprint",
    "confirm_object_dn",
    "confirmation_phrase",
})


class AclDelegationWriteTrustBadRequest(ValueError):
    pass


@dataclass(frozen=True)
class AclDelegationWriteTrustedEvidence:
    intent: AclDelegationWriteIntent
    binding: AclDelegationWriteBinding
    simulation_job_id: str
    security_descriptor_job_id: str
    target_object_guid: str
    simulation_completed_at: str
    security_descriptor_completed_at: str
    simulation_age_seconds: float
    security_descriptor_age_seconds: float
    evidence_digest: str
    trusted_source: str
    trusted_evidence_loaded: bool
    binding_validated: bool
    job_creation_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    ad_write_authorized: bool


def _strict_canonical_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise AclDelegationWriteTrustBadRequest(
            "L'intention ACL doit etre un objet"
        )

    for key in payload:
        if not isinstance(key, str):
            raise AclDelegationWriteTrustBadRequest(
                "Cle non textuelle interdite"
            )

    unexpected = sorted(
        set(payload) - CANONICAL_INTENT_KEYS
    )

    if unexpected:
        raise AclDelegationWriteTrustBadRequest(
            "Champs non autorises dans l'intention ACL : "
            + ", ".join(unexpected)
        )

    return dict(payload)


def _normalize_now(
    now: datetime | None,
) -> datetime:
    resolved = (
        now
        if now is not None
        else datetime.now(timezone.utc)
    )

    if not isinstance(resolved, datetime):
        raise AclDelegationWriteTrustBadRequest(
            "Horodatage de validation invalide"
        )

    if resolved.tzinfo is None:
        raise AclDelegationWriteTrustBadRequest(
            "Horodatage de validation sans fuseau"
        )

    return resolved.astimezone(timezone.utc)


def _parse_timestamp(
    value,
    field_name: str,
) -> datetime:
    raw = str(value or "").strip()

    if not raw:
        raise AclDelegationWriteTrustBadRequest(
            f"{field_name} absent"
        )

    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise AclDelegationWriteTrustBadRequest(
            f"{field_name} invalide"
        ) from exc

    if parsed.tzinfo is None:
        raise AclDelegationWriteTrustBadRequest(
            f"{field_name} doit etre timezone-aware"
        )

    return parsed.astimezone(timezone.utc)


def _assert_fresh(
    completed_at: datetime,
    now: datetime,
    max_age_seconds: int,
    label: str,
) -> float:
    future_seconds = (
        completed_at - now
    ).total_seconds()

    if (
        future_seconds
        > ACL_DELEGATION_WRITE_MAX_CLOCK_SKEW_SECONDS
    ):
        raise AclDelegationWriteTrustBadRequest(
            f"{label} date dans le futur"
        )

    age_seconds = max(
        0.0,
        (now - completed_at).total_seconds(),
    )

    if age_seconds > max_age_seconds:
        raise AclDelegationWriteTrustBadRequest(
            f"{label} trop ancien"
        )

    return age_seconds


def _load_exact_job(
    jobs_file: Path,
    job_id: str,
    label: str,
) -> dict:
    path = Path(jobs_file)

    if not path.exists() or not path.is_file():
        raise AclDelegationWriteTrustBadRequest(
            f"Stockage {label} indisponible"
        )

    data = load_json(path, None)

    if not isinstance(data, list):
        raise AclDelegationWriteTrustBadRequest(
            f"Stockage {label} invalide"
        )

    for item in data:
        if not isinstance(item, dict):
            raise AclDelegationWriteTrustBadRequest(
                f"Integrite du stockage {label} invalide"
            )

    matches = [
        item
        for item in data
        if (
            str(item.get("id") or "")
            .strip()
            .lower()
            == job_id.lower()
        )
    ]

    if len(matches) != 1:
        raise AclDelegationWriteTrustBadRequest(
            f"Preuve {label} introuvable ou ambigue"
        )

    return deepcopy(matches[0])


def _build_evidence_digest(
    intent: AclDelegationWriteIntent,
    binding: AclDelegationWriteBinding,
    simulation_completed_at: str,
    security_completed_at: str,
) -> str:
    material = {
        "action": "apply_acl_delegation",
        "target_dn": binding.target_dn,
        "target_object_guid": (
            binding.target_object_guid
        ),
        "principal_dn": binding.principal_dn,
        "principal_sid": binding.principal_sid,
        "access_control_type": (
            intent.access_control_type
        ),
        "rights": sorted(
            intent.rights,
            key=str.casefold,
        ),
        "inheritance_type": (
            intent.inheritance_type
        ),
        "object_type_guid": (
            intent.object_type_guid
        ),
        "inherited_object_type_guid": (
            intent.inherited_object_type_guid
        ),
        "simulation_job_id": (
            binding.simulation_job_id
        ),
        "security_descriptor_job_id": (
            binding.security_descriptor_job_id
        ),
        "simulation_completed_at": (
            simulation_completed_at
        ),
        "security_descriptor_completed_at": (
            security_completed_at
        ),
        "acl_fingerprint": (
            binding.acl_fingerprint
        ),
    }

    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def resolve_trusted_acl_delegation_write_evidence(
    *,
    ad_admin_jobs_file: Path,
    ad_explorer_jobs_file: Path,
    intent_payload: dict,
    now: datetime | None = None,
) -> AclDelegationWriteTrustedEvidence:
    if not ACL_DELEGATION_WRITE_TRUST_ENABLED:
        raise AclDelegationWriteTrustBadRequest(
            "Resolution de confiance ACL desactivee"
        )

    canonical_payload = _strict_canonical_payload(
        intent_payload
    )

    try:
        intent = normalize_acl_delegation_write_intent(
            canonical_payload
        )
    except AclDelegationWriteIntentBadRequest as exc:
        raise AclDelegationWriteTrustBadRequest(
            str(exc)
        ) from exc

    if (
        intent.simulation_job_id
        == intent.security_descriptor_job_id
    ):
        raise AclDelegationWriteTrustBadRequest(
            "Les deux preuves doivent utiliser "
            "des identifiants distincts"
        )

    admin_path = Path(
        ad_admin_jobs_file
    ).resolve()

    explorer_path = Path(
        ad_explorer_jobs_file
    ).resolve()

    if admin_path == explorer_path:
        raise AclDelegationWriteTrustBadRequest(
            "Les stockages de preuve doivent etre distincts"
        )

    simulation_job = _load_exact_job(
        admin_path,
        intent.simulation_job_id,
        "Simulation",
    )

    security_job = _load_exact_job(
        explorer_path,
        intent.security_descriptor_job_id,
        "Security Descriptor",
    )

    try:
        binding = validate_acl_delegation_write_binding(
            canonical_payload,
            simulation_job,
            security_job,
        )
    except AclDelegationWriteBindingBadRequest as exc:
        raise AclDelegationWriteTrustBadRequest(
            str(exc)
        ) from exc

    validation_time = _normalize_now(now)

    simulation_completed = _parse_timestamp(
        simulation_job.get("completed_at"),
        "simulation.completed_at",
    )

    security_completed = _parse_timestamp(
        security_job.get("completed_at"),
        "security_descriptor.completed_at",
    )

    simulation_age = _assert_fresh(
        simulation_completed,
        validation_time,
        ACL_DELEGATION_WRITE_MAX_SIMULATION_AGE_SECONDS,
        "Simulation ACL",
    )

    security_age = _assert_fresh(
        security_completed,
        validation_time,
        ACL_DELEGATION_WRITE_MAX_DESCRIPTOR_AGE_SECONDS,
        "Security Descriptor",
    )

    simulation_completed_text = (
        simulation_completed.isoformat()
    )

    security_completed_text = (
        security_completed.isoformat()
    )

    evidence_digest = _build_evidence_digest(
        intent,
        binding,
        simulation_completed_text,
        security_completed_text,
    )

    return AclDelegationWriteTrustedEvidence(
        intent=intent,
        binding=binding,
        simulation_job_id=(
            binding.simulation_job_id
        ),
        security_descriptor_job_id=(
            binding.security_descriptor_job_id
        ),
        target_object_guid=(
            binding.target_object_guid
        ),
        simulation_completed_at=(
            simulation_completed_text
        ),
        security_descriptor_completed_at=(
            security_completed_text
        ),
        simulation_age_seconds=simulation_age,
        security_descriptor_age_seconds=(
            security_age
        ),
        evidence_digest=evidence_digest,
        trusted_source="server_job_storage",
        trusted_evidence_loaded=True,
        binding_validated=True,
        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,
    )


def assert_acl_delegation_write_trust_invariants(
) -> None:
    if not ACL_DELEGATION_WRITE_TRUST_ENABLED:
        raise RuntimeError(
            "C8.4B1 trusted resolution "
            "must remain enabled"
        )

    if ACL_DELEGATION_WRITE_TRUST_JOB_CREATION_ENABLED:
        raise RuntimeError(
            "C8.4B1 job creation must remain disabled"
        )

    if ACL_DELEGATION_WRITE_TRUST_RUNTIME_ENABLED:
        raise RuntimeError(
            "C8.4B1 runtime must remain disabled"
        )

    if ACL_DELEGATION_WRITE_TRUST_PRODUCTION_ENABLED:
        raise RuntimeError(
            "C8.4B1 Production must remain disabled"
        )

    if ACL_DELEGATION_WRITE_TRUST_AD_WRITE_ENABLED:
        raise RuntimeError(
            "C8.4B1 AD writes must remain disabled"
        )


assert_acl_delegation_write_trust_invariants()
