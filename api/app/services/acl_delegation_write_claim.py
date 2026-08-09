from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.security import AuthenticatedIdentity
from app.services.acl_delegation_write_identity_envelope import (
    AclDelegationWriteIdentityEnvelope,
    AclDelegationWriteIdentityEnvelopeError,
    build_acl_delegation_write_identity_envelope,
)
from app.services.acl_delegation_write_replay import (
    REGISTRY_MAX_RECORDS,
    AclDelegationWriteReplayConflict,
    AclDelegationWriteReplayStorageError,
    _atomic_write_registry,
    _exclusive_registry_lock,
    _normalize_registry_path,
    _safe_load_registry,
)


ACL_DELEGATION_WRITE_CLAIM_CONTRACT_VERSION = (
    "c8.4b4"
)

ACL_DELEGATION_WRITE_CLAIM_ENABLED = True

ACL_DELEGATION_WRITE_CLAIM_JOB_CREATION_ENABLED = False
ACL_DELEGATION_WRITE_CLAIM_RUNTIME_ENABLED = False
ACL_DELEGATION_WRITE_CLAIM_PRODUCTION_ENABLED = False
ACL_DELEGATION_WRITE_CLAIM_AD_WRITE_ENABLED = False


class AclDelegationWriteClaimError(ValueError):
    pass


class AclDelegationWriteClaimConflict(
    AclDelegationWriteClaimError
):
    pass


@dataclass(frozen=True)
class AclDelegationWriteClaim:
    claim_id: str
    consumption_id: str
    contract_version: str
    state: str

    envelope_digest: str
    evidence_digest: str

    simulation_job_id: str
    security_descriptor_job_id: str

    target_dn: str
    target_object_guid: str

    principal_dn: str
    principal_sid: str

    access_control_type: str
    rights: tuple[str, ...]
    inheritance_type: str
    object_type_guid: str | None
    inherited_object_type_guid: str | None

    dacl_sddl_sha256: str
    acl_fingerprint: str

    actor_subject: str
    actor_username: str
    actor_roles: tuple[str, ...]
    actor_issuer: str
    actor_azp: str
    actor_jti: str | None

    server_nonce: str
    issued_at: str
    expires_at: str
    claimed_at: str

    replay_consumed: bool

    job_creation_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    ad_write_authorized: bool


def _normalize_now(
    now: datetime | None,
) -> datetime:
    resolved = (
        now
        if now is not None
        else datetime.now(timezone.utc)
    )

    if not isinstance(resolved, datetime):
        raise AclDelegationWriteClaimError(
            "Horodatage claim ACL invalide"
        )

    if resolved.tzinfo is None:
        raise AclDelegationWriteClaimError(
            "Horodatage claim ACL sans fuseau"
        )

    return resolved.astimezone(
        timezone.utc
    )


def _assert_envelope_safe(
    envelope: AclDelegationWriteIdentityEnvelope,
) -> None:
    if envelope.trusted_evidence_loaded is not True:
        raise AclDelegationWriteClaimError(
            "Preuve serveur du claim non chargee"
        )

    if envelope.binding_validated is not True:
        raise AclDelegationWriteClaimError(
            "Binding du claim non valide"
        )

    if envelope.replay_consumed is not False:
        raise AclDelegationWriteClaimError(
            "Enveloppe deja consommee"
        )

    if envelope.replay_consumption_id is not None:
        raise AclDelegationWriteClaimError(
            "Consumption ID premature"
        )

    if envelope.replay_consumption_required is not True:
        raise AclDelegationWriteClaimError(
            "Anti-replay non requis"
        )

    if any((
        envelope.job_creation_authorized,
        envelope.runtime_authorized,
        envelope.production_authorized,
        envelope.ad_write_authorized,
    )):
        raise AclDelegationWriteClaimError(
            "Enveloppe ACL autorisante interdite"
        )


def _assert_not_consumed(
    records: list,
    envelope: AclDelegationWriteIdentityEnvelope,
) -> None:
    digest = envelope.evidence_digest.lower()
    simulation_id = envelope.simulation_job_id.lower()
    descriptor_id = (
        envelope.security_descriptor_job_id.lower()
    )

    for record in records:
        if (
            str(
                record.get("evidence_digest")
                or ""
            ).lower()
            == digest
        ):
            raise AclDelegationWriteClaimConflict(
                "Preuve ACL deja consommee"
            )

        if (
            str(
                record.get("simulation_job_id")
                or ""
            ).lower()
            == simulation_id
        ):
            raise AclDelegationWriteClaimConflict(
                "Simulation ACL deja consommee"
            )

        if (
            str(
                record.get(
                    "security_descriptor_job_id"
                )
                or ""
            ).lower()
            == descriptor_id
        ):
            raise AclDelegationWriteClaimConflict(
                "Security Descriptor deja consomme"
            )


def claim_acl_delegation_write_intent(
    *,
    identity: AuthenticatedIdentity,
    ad_admin_jobs_file: Path,
    ad_explorer_jobs_file: Path,
    replay_registry_file: Path,
    intent_payload: dict,
    now: datetime | None = None,
) -> AclDelegationWriteClaim:
    if not ACL_DELEGATION_WRITE_CLAIM_ENABLED:
        raise AclDelegationWriteClaimError(
            "Claim ACL B4 desactive"
        )

    registry_path = (
        _normalize_registry_path(
            replay_registry_file
        )
    )

    with _exclusive_registry_lock(
        registry_path
    ):
        # Freshness and OIDC envelope validation happen only
        # after obtaining the same interprocess lock that
        # protects anti-replay consumption.
        claim_now = _normalize_now(
            now
        )

        try:
            envelope = (
                build_acl_delegation_write_identity_envelope(
                    identity=identity,
                    ad_admin_jobs_file=(
                        ad_admin_jobs_file
                    ),
                    ad_explorer_jobs_file=(
                        ad_explorer_jobs_file
                    ),
                    intent_payload=intent_payload,
                    now=claim_now,
                )
            )
        except AclDelegationWriteIdentityEnvelopeError as exc:
            raise AclDelegationWriteClaimError(
                str(exc)
            ) from exc

        _assert_envelope_safe(
            envelope
        )

        registry = _safe_load_registry(
            registry_path
        )

        claim_id = str(
            uuid.uuid4()
        )

        consumption_id = str(
            uuid.uuid4()
        )

        claimed_at = (
            claim_now.isoformat()
        )

        records = registry["records"]

        _assert_not_consumed(
            records,
            envelope,
        )

        if len(records) >= REGISTRY_MAX_RECORDS:
            raise AclDelegationWriteReplayStorageError(
                "Registre anti-replay ACL plein"
            )

        record = {
            "consumption_id": consumption_id,
            "evidence_digest": (
                envelope.evidence_digest
            ),
            "simulation_job_id": (
                envelope.simulation_job_id
            ),
            "security_descriptor_job_id": (
                envelope.security_descriptor_job_id
            ),
            "target_dn": envelope.target_dn,
            "target_object_guid": (
                envelope.target_object_guid
            ),
            "principal_dn": (
                envelope.principal_dn
            ),
            "principal_sid": (
                envelope.principal_sid
            ),

            "access_control_type": (
                envelope.access_control_type
            ),
            "rights": list(
                envelope.rights
            ),
            "inheritance_type": (
                envelope.inheritance_type
            ),
            "object_type_guid": (
                envelope.object_type_guid
            ),
            "inherited_object_type_guid": (
                envelope.inherited_object_type_guid
            ),

            "dacl_sddl_sha256": (
                envelope.dacl_sddl_sha256
            ),
            "acl_fingerprint": (
                envelope.acl_fingerprint
            ),

            "consumed_at": claimed_at,
            "state": "claimed_dormant",

            "claim_id": claim_id,
            "contract_version_claim": (
                ACL_DELEGATION_WRITE_CLAIM_CONTRACT_VERSION
            ),
            "envelope_digest": (
                envelope.envelope_digest
            ),
            "server_nonce": (
                envelope.server_nonce
            ),

            "actor_subject": (
                envelope.actor_subject
            ),
            "actor_username": (
                envelope.actor_username
            ),
            "actor_roles": list(
                envelope.actor_roles
            ),
            "actor_issuer": (
                envelope.actor_issuer
            ),
            "actor_azp": (
                envelope.actor_azp
            ),
            "actor_jti": (
                envelope.actor_jti
            ),

            "issued_at": envelope.issued_at,
            "expires_at": envelope.expires_at,
            "claimed_at": claimed_at,

            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        }

        records.append(
            record
        )

        _atomic_write_registry(
            registry_path,
            registry,
        )

    return AclDelegationWriteClaim(
        claim_id=claim_id,
        consumption_id=consumption_id,
        contract_version=(
            ACL_DELEGATION_WRITE_CLAIM_CONTRACT_VERSION
        ),
        state="claimed_dormant",

        envelope_digest=(
            envelope.envelope_digest
        ),
        evidence_digest=(
            envelope.evidence_digest
        ),

        simulation_job_id=(
            envelope.simulation_job_id
        ),
        security_descriptor_job_id=(
            envelope.security_descriptor_job_id
        ),

        target_dn=envelope.target_dn,
        target_object_guid=(
            envelope.target_object_guid
        ),

        principal_dn=(
            envelope.principal_dn
        ),
        principal_sid=(
            envelope.principal_sid
        ),

        access_control_type=(
            envelope.access_control_type
        ),
        rights=envelope.rights,
        inheritance_type=(
            envelope.inheritance_type
        ),
        object_type_guid=(
            envelope.object_type_guid
        ),
        inherited_object_type_guid=(
            envelope.inherited_object_type_guid
        ),

        dacl_sddl_sha256=(
            envelope.dacl_sddl_sha256
        ),
        acl_fingerprint=(
            envelope.acl_fingerprint
        ),

        actor_subject=(
            envelope.actor_subject
        ),
        actor_username=(
            envelope.actor_username
        ),
        actor_roles=(
            envelope.actor_roles
        ),
        actor_issuer=(
            envelope.actor_issuer
        ),
        actor_azp=(
            envelope.actor_azp
        ),
        actor_jti=(
            envelope.actor_jti
        ),

        server_nonce=(
            envelope.server_nonce
        ),
        issued_at=envelope.issued_at,
        expires_at=envelope.expires_at,
        claimed_at=claimed_at,

        replay_consumed=True,

        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,
    )


def assert_acl_delegation_write_claim_invariants(
) -> None:
    if not ACL_DELEGATION_WRITE_CLAIM_ENABLED:
        raise RuntimeError(
            "C8.4B4 claim must remain enabled"
        )

    if ACL_DELEGATION_WRITE_CLAIM_JOB_CREATION_ENABLED:
        raise RuntimeError(
            "C8.4B4 job creation must remain disabled"
        )

    if ACL_DELEGATION_WRITE_CLAIM_RUNTIME_ENABLED:
        raise RuntimeError(
            "C8.4B4 runtime must remain disabled"
        )

    if ACL_DELEGATION_WRITE_CLAIM_PRODUCTION_ENABLED:
        raise RuntimeError(
            "C8.4B4 Production must remain disabled"
        )

    if ACL_DELEGATION_WRITE_CLAIM_AD_WRITE_ENABLED:
        raise RuntimeError(
            "C8.4B4 AD writes must remain disabled"
        )


assert_acl_delegation_write_claim_invariants()
