from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.services.acl_delegation_write_binding import (
    AclDelegationWriteBindingBadRequest,
    calculate_acl_fingerprint,
)
from app.services.acl_delegation_write_intent import (
    ACL_DELEGATION_WRITE_CONFIRMATION_PHRASE,
)
from app.services.acl_delegation_write_trust import (
    AclDelegationWriteTrustBadRequest,
    _load_exact_job,
    resolve_trusted_acl_delegation_write_evidence,
)


ACL_DELEGATION_PRODUCTION_PREPARATION_CONTRACT_VERSION = (
    "c8.4d-a3b2b1"
)

ACL_DELEGATION_PRODUCTION_PREPARATION_ENABLED = True

# C8.4D-A3B2B1 only prepares trusted server evidence.
# It must never persist a claim or authorize execution.
ACL_DELEGATION_PRODUCTION_PREPARATION_PERSISTENCE_ENABLED = (
    False
)
ACL_DELEGATION_PRODUCTION_PREPARATION_JOB_CREATION_AUTHORIZED = (
    False
)
ACL_DELEGATION_PRODUCTION_PREPARATION_RUNTIME_AUTHORIZED = (
    False
)
ACL_DELEGATION_PRODUCTION_PREPARATION_PRODUCTION_AUTHORIZED = (
    False
)
ACL_DELEGATION_PRODUCTION_PREPARATION_AD_WRITE_AUTHORIZED = (
    False
)


class AclDelegationProductionPreparationError(
    ValueError
):
    pass


@dataclass(frozen=True)
class AclDelegationProductionPreparation:
    contract_version: str
    state: str

    simulation_job_id: str
    security_descriptor_job_id: str

    target_dn: str
    target_object_guid: str

    principal_identity: str
    principal_dn: str
    principal_sid: str

    access_control_type: str
    rights: tuple[str, ...]
    inheritance_type: str
    object_type_guid: str | None
    inherited_object_type_guid: str | None

    dacl_sddl_sha256: str
    acl_fingerprint: str
    evidence_digest: str

    simulation_completed_at: str
    security_descriptor_completed_at: str
    simulation_age_seconds: float
    security_descriptor_age_seconds: float

    required_confirm_object_dn: str
    required_confirmation_phrase: str

    trusted_source: str
    trusted_evidence_loaded: bool
    binding_validated: bool

    human_confirmation_validated: bool
    replay_consumed: bool
    claim_created: bool

    job_creation_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    ad_write_authorized: bool


def _clean_string(value) -> str:
    return str(
        value or ""
    ).strip()


def _normalize_uuid(
    value,
    field_name: str,
) -> str:
    raw = _clean_string(
        value
    )

    if not raw:
        raise AclDelegationProductionPreparationError(
            field_name
            + " obligatoire"
        )

    try:
        return str(
            UUID(raw)
        ).lower()

    except (
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:
        raise AclDelegationProductionPreparationError(
            field_name
            + " invalide"
        ) from exc


def _strict_request(
    payload: dict,
) -> tuple[str, str]:
    if not isinstance(
        payload,
        dict,
    ):
        raise AclDelegationProductionPreparationError(
            "Preparation ACL invalide"
        )

    allowed = {
        "simulation_job_id",
        "security_descriptor_job_id",
    }

    unexpected = sorted(
        set(payload)
        - allowed
    )

    if unexpected:
        raise AclDelegationProductionPreparationError(
            "Champs preparation ACL interdits : "
            + ", ".join(
                unexpected
            )
        )

    simulation_job_id = _normalize_uuid(
        payload.get(
            "simulation_job_id"
        ),
        "simulation_job_id",
    )

    security_descriptor_job_id = (
        _normalize_uuid(
            payload.get(
                "security_descriptor_job_id"
            ),
            "security_descriptor_job_id",
        )
    )

    if (
        simulation_job_id
        == security_descriptor_job_id
    ):
        raise AclDelegationProductionPreparationError(
            "Les preuves ACL doivent etre distinctes"
        )

    return (
        simulation_job_id,
        security_descriptor_job_id,
    )


def _extract_descriptor(
    job: dict,
) -> dict:
    result = job.get(
        "result"
    )

    if isinstance(
        result,
        dict,
    ):
        return result

    output = job.get(
        "output"
    )

    if isinstance(
        output,
        dict,
    ):
        return output

    raise AclDelegationProductionPreparationError(
        "Security Descriptor serveur absent"
    )


def _required_simulation_value(
    payload: dict,
    key: str,
):
    value = payload.get(
        key
    )

    if value is None:
        raise AclDelegationProductionPreparationError(
            "Champ Simulation ACL absent : "
            + key
        )

    if (
        isinstance(value, str)
        and not value.strip()
    ):
        raise AclDelegationProductionPreparationError(
            "Champ Simulation ACL vide : "
            + key
        )

    return value


def prepare_acl_delegation_production_evidence(
    *,
    ad_admin_jobs_file: Path,
    ad_explorer_jobs_file: Path,
    payload: dict,
    now: datetime | None = None,
) -> AclDelegationProductionPreparation:
    if not (
        ACL_DELEGATION_PRODUCTION_PREPARATION_ENABLED
    ):
        raise AclDelegationProductionPreparationError(
            "Preparation Production ACL desactivee"
        )

    (
        simulation_job_id,
        security_descriptor_job_id,
    ) = _strict_request(
        payload
    )

    admin_path = Path(
        ad_admin_jobs_file
    ).resolve()

    explorer_path = Path(
        ad_explorer_jobs_file
    ).resolve()

    if admin_path == explorer_path:
        raise AclDelegationProductionPreparationError(
            "Stockages de preuves ACL invalides"
        )

    try:
        simulation_job = _load_exact_job(
            admin_path,
            simulation_job_id,
            "Simulation",
        )

        security_job = _load_exact_job(
            explorer_path,
            security_descriptor_job_id,
            "Security Descriptor",
        )

    except AclDelegationWriteTrustBadRequest as exc:
        raise AclDelegationProductionPreparationError(
            str(exc)
        ) from exc

    simulation_payload = simulation_job.get(
        "payload"
    )

    if not isinstance(
        simulation_payload,
        dict,
    ):
        raise AclDelegationProductionPreparationError(
            "Payload de Simulation ACL absent"
        )

    descriptor = _extract_descriptor(
        security_job
    )

    try:
        fingerprint = calculate_acl_fingerprint(
            descriptor
        )

    except AclDelegationWriteBindingBadRequest as exc:
        raise AclDelegationProductionPreparationError(
            str(exc)
        ) from exc

    object_dn = _clean_string(
        _required_simulation_value(
            simulation_payload,
            "object_dn",
        )
    )

    principal_identity = _clean_string(
        _required_simulation_value(
            simulation_payload,
            "principal_identity",
        )
    )

    access_control_type = _clean_string(
        _required_simulation_value(
            simulation_payload,
            "access_control_type",
        )
    )

    rights = _required_simulation_value(
        simulation_payload,
        "rights",
    )

    inheritance_type = _clean_string(
        _required_simulation_value(
            simulation_payload,
            "inheritance_type",
        )
    )

    candidate_intent = {
        "action": "apply_acl_delegation",
        "mode": "Production",

        "object_dn": object_dn,
        "principal_identity": (
            principal_identity
        ),

        "access_control_type": (
            access_control_type
        ),
        "rights": rights,
        "inheritance_type": (
            inheritance_type
        ),

        "object_type_guid": (
            simulation_payload.get(
                "object_type_guid"
            )
        ),

        "inherited_object_type_guid": (
            simulation_payload.get(
                "inherited_object_type_guid"
            )
        ),

        "simulation_job_id": (
            simulation_job_id
        ),

        "security_descriptor_job_id": (
            security_descriptor_job_id
        ),

        "expected_acl_fingerprint": (
            fingerprint
        ),

        # These values are inserted only so the existing
        # dormant C8.4A/B validation stack can validate
        # the complete evidence contract.
        #
        # This preparation service does NOT claim that
        # a human entered or validated them.
        "confirm_object_dn": object_dn,
        "confirmation_phrase": (
            ACL_DELEGATION_WRITE_CONFIRMATION_PHRASE
        ),
    }

    try:
        evidence = (
            resolve_trusted_acl_delegation_write_evidence(
                ad_admin_jobs_file=admin_path,
                ad_explorer_jobs_file=(
                    explorer_path
                ),
                intent_payload=(
                    candidate_intent
                ),
                now=now,
            )
        )

    except AclDelegationWriteTrustBadRequest as exc:
        raise AclDelegationProductionPreparationError(
            str(exc)
        ) from exc

    if evidence.trusted_evidence_loaded is not True:
        raise AclDelegationProductionPreparationError(
            "Preuve ACL serveur non chargee"
        )

    if evidence.binding_validated is not True:
        raise AclDelegationProductionPreparationError(
            "Binding ACL serveur non valide"
        )

    if any((
        evidence.job_creation_authorized,
        evidence.runtime_authorized,
        evidence.production_authorized,
        evidence.ad_write_authorized,
    )):
        raise AclDelegationProductionPreparationError(
            "Preparation ACL autorisante interdite"
        )

    binding = evidence.binding
    intent = evidence.intent

    if (
        binding.acl_fingerprint
        != fingerprint
    ):
        raise AclDelegationProductionPreparationError(
            "Fingerprint ACL serveur incoherent"
        )

    return AclDelegationProductionPreparation(
        contract_version=(
            ACL_DELEGATION_PRODUCTION_PREPARATION_CONTRACT_VERSION
        ),

        state=(
            "production_preparation_dormant"
        ),

        simulation_job_id=(
            evidence.simulation_job_id
        ),

        security_descriptor_job_id=(
            evidence.security_descriptor_job_id
        ),

        target_dn=(
            binding.target_dn
        ),

        target_object_guid=(
            binding.target_object_guid
        ),

        principal_identity=(
            principal_identity
        ),

        principal_dn=(
            binding.principal_dn
        ),

        principal_sid=(
            binding.principal_sid
        ),

        access_control_type=(
            intent.access_control_type
        ),

        rights=tuple(
            intent.rights
        ),

        inheritance_type=(
            intent.inheritance_type
        ),

        object_type_guid=(
            intent.object_type_guid
        ),

        inherited_object_type_guid=(
            intent.inherited_object_type_guid
        ),

        dacl_sddl_sha256=(
            binding.dacl_sddl_sha256
        ),

        acl_fingerprint=(
            binding.acl_fingerprint
        ),

        evidence_digest=(
            evidence.evidence_digest
        ),

        simulation_completed_at=(
            evidence.simulation_completed_at
        ),

        security_descriptor_completed_at=(
            evidence.security_descriptor_completed_at
        ),

        simulation_age_seconds=(
            evidence.simulation_age_seconds
        ),

        security_descriptor_age_seconds=(
            evidence.security_descriptor_age_seconds
        ),

        required_confirm_object_dn=(
            binding.target_dn
        ),

        required_confirmation_phrase=(
            ACL_DELEGATION_WRITE_CONFIRMATION_PHRASE
        ),

        trusted_source=(
            evidence.trusted_source
        ),

        trusted_evidence_loaded=True,
        binding_validated=True,

        # Important:
        # preparation is not human confirmation.
        human_confirmation_validated=False,

        replay_consumed=False,
        claim_created=False,

        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,
    )


def assert_acl_delegation_production_preparation_invariants(
) -> None:
    if not ACL_DELEGATION_PRODUCTION_PREPARATION_ENABLED:
        raise RuntimeError(
            "C8.4D-A3B2B1 preparation must remain enabled"
        )

    if (
        ACL_DELEGATION_PRODUCTION_PREPARATION_PERSISTENCE_ENABLED
    ):
        raise RuntimeError(
            "C8.4D-A3B2B1 persistence must remain disabled"
        )

    if (
        ACL_DELEGATION_PRODUCTION_PREPARATION_JOB_CREATION_AUTHORIZED
    ):
        raise RuntimeError(
            "C8.4D-A3B2B1 job creation must remain disabled"
        )

    if (
        ACL_DELEGATION_PRODUCTION_PREPARATION_RUNTIME_AUTHORIZED
    ):
        raise RuntimeError(
            "C8.4D-A3B2B1 runtime must remain disabled"
        )

    if (
        ACL_DELEGATION_PRODUCTION_PREPARATION_PRODUCTION_AUTHORIZED
    ):
        raise RuntimeError(
            "C8.4D-A3B2B1 Production must remain unauthorized"
        )

    if (
        ACL_DELEGATION_PRODUCTION_PREPARATION_AD_WRITE_AUTHORIZED
    ):
        raise RuntimeError(
            "C8.4D-A3B2B1 AD writes must remain unauthorized"
        )


assert_acl_delegation_production_preparation_invariants()
