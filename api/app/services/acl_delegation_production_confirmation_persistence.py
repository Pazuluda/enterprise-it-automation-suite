import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.services.acl_delegation_production_confirmation import (
    AclDelegationProductionConfirmationConflict,
    _normalize_now,
    _validate_confirmation,
)
from app.services.acl_delegation_write_replay import (
    AclDelegationWriteReplayStorageError,
    _atomic_write_registry,
    _exclusive_registry_lock,
    _normalize_registry_path,
    _safe_load_registry,
)


ACL_DELEGATION_PRODUCTION_CONFIRMATION_PERSISTENCE_CONTRACT_VERSION = (
    "c8.4d-a2c1"
)

ACL_DELEGATION_PRODUCTION_CONFIRMATION_PERSISTENCE_ENABLED = True

# C8.4D-A2C1 persists a consumed human confirmation only.
# It still does not authorize a job, runtime, Production
# execution or an Active Directory write.
ACL_DELEGATION_PRODUCTION_CONFIRMATION_JOB_CREATION_AUTHORIZED = False
ACL_DELEGATION_PRODUCTION_CONFIRMATION_RUNTIME_AUTHORIZED = False
ACL_DELEGATION_PRODUCTION_CONFIRMATION_PRODUCTION_AUTHORIZED = False
ACL_DELEGATION_PRODUCTION_CONFIRMATION_AD_WRITE_AUTHORIZED = False


class AclDelegationProductionConfirmationPersistenceError(
    ValueError
):
    pass


class AclDelegationProductionConfirmationPersistenceConflict(
    AclDelegationProductionConfirmationPersistenceError
):
    pass


@dataclass(frozen=True)
class AclDelegationProductionConfirmationPersistence:
    contract_version: str
    state: str
    source_state: str

    confirmation_id: str
    confirmation_digest: str
    confirmation_created_at: str

    claim_id: str
    ticket_id: str
    execution_id: str

    actor_subject: str
    actor_username: str

    target_dn: str
    target_object_guid: str

    principal_sid: str

    dacl_sddl_sha256: str
    acl_fingerprint: str

    confirmation_validated: bool
    confirmation_consumed: bool

    job_creation_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    ad_write_authorized: bool


def _clean_string(value) -> str:
    return str(
        value or ""
    ).strip()


def _find_record(
    registry: dict,
    claim_id: str,
) -> dict:
    normalized = _clean_string(
        claim_id
    ).casefold()

    if not normalized:
        raise AclDelegationProductionConfirmationPersistenceError(
            "claim_id ACL obligatoire"
        )

    records = registry.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise AclDelegationWriteReplayStorageError(
            "Registre ACL invalide"
        )

    matches = [
        record
        for record in records
        if isinstance(record, dict)
        and _clean_string(
            record.get("claim_id")
        ).casefold()
        == normalized
    ]

    if not matches:
        raise AclDelegationProductionConfirmationPersistenceError(
            "Claim ACL introuvable"
        )

    if len(matches) != 1:
        raise AclDelegationWriteReplayStorageError(
            "claim_id ACL duplique"
        )

    return matches[0]


def _build_confirmation_digest(
    *,
    confirmation_id: str,
    confirmation,
    created_at: str,
) -> str:
    material = {
        "contract_version": (
            ACL_DELEGATION_PRODUCTION_CONFIRMATION_PERSISTENCE_CONTRACT_VERSION
        ),
        "confirmation_id": confirmation_id,
        "created_at": created_at,

        "claim_id": confirmation.claim_id,
        "ticket_id": confirmation.ticket_id,
        "execution_id": confirmation.execution_id,

        "actor_subject": (
            confirmation.actor_subject
        ),
        "actor_username": (
            confirmation.actor_username
        ),
        "actor_issuer": (
            confirmation.actor_issuer
        ),
        "actor_azp": confirmation.actor_azp,

        "target_dn": confirmation.target_dn,
        "target_object_guid": (
            confirmation.target_object_guid
        ),

        "principal_sid": (
            confirmation.principal_sid
        ),

        "dacl_sddl_sha256": (
            confirmation.dacl_sddl_sha256
        ),
        "acl_fingerprint": (
            confirmation.acl_fingerprint
        ),

        "prewrite_completed_at": (
            confirmation.prewrite_completed_at
        ),

        "confirm_object_dn": (
            confirmation.confirm_object_dn
        ),

        "confirmation_phrase_sha256": (
            hashlib.sha256(
                confirmation.confirmation_phrase.encode(
                    "utf-8"
                )
            ).hexdigest()
        ),
    }

    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def persist_acl_delegation_production_confirmation(
    *,
    identity,
    replay_registry_file: Path,
    claim_id: str,
    ticket_id: str,
    execution_id: str,
    confirm_object_dn: str,
    confirmation_phrase: str,
    now: datetime | None = None,
) -> AclDelegationProductionConfirmationPersistence:
    if not ACL_DELEGATION_PRODUCTION_CONFIRMATION_PERSISTENCE_ENABLED:
        raise AclDelegationProductionConfirmationPersistenceError(
            "Persistance confirmation ACL desactivee"
        )

    confirmation_now = _normalize_now(
        now
    )

    registry_path = _normalize_registry_path(
        replay_registry_file
    )

    with _exclusive_registry_lock(
        registry_path
    ):
        registry = _safe_load_registry(
            registry_path
        )

        record = _find_record(
            registry,
            claim_id,
        )

        if record.get(
            "production_confirmation_consumed"
        ) is True:
            raise AclDelegationProductionConfirmationPersistenceConflict(
                "Confirmation Production ACL deja consommee"
            )

        if any(
            record.get(key)
            for key in (
                "production_confirmation_id",
                "production_confirmation_digest",
                "production_confirmation_created_at",
            )
        ):
            raise AclDelegationWriteReplayStorageError(
                "Confirmation Production ACL partiellement persistee"
            )

        try:
            confirmation = _validate_confirmation(
                record=record,
                identity=identity,
                claim_id=claim_id,
                ticket_id=ticket_id,
                execution_id=execution_id,
                confirm_object_dn=confirm_object_dn,
                confirmation_phrase=confirmation_phrase,
                now=confirmation_now,
            )

        except AclDelegationProductionConfirmationConflict:
            raise

        confirmation_id = str(
            uuid.uuid4()
        )

        created_at = (
            confirmation_now.isoformat()
        )

        confirmation_digest = (
            _build_confirmation_digest(
                confirmation_id=confirmation_id,
                confirmation=confirmation,
                created_at=created_at,
            )
        )

        phrase_sha256 = hashlib.sha256(
            confirmation.confirmation_phrase.encode(
                "utf-8"
            )
        ).hexdigest()

        # Keep the proven C8.4C state intact.
        if record.get("state") != "prewrite_validated":
            raise AclDelegationWriteReplayStorageError(
                "Etat pre-write modifie pendant confirmation"
            )

        record[
            "production_confirmation_contract_version"
        ] = (
            ACL_DELEGATION_PRODUCTION_CONFIRMATION_PERSISTENCE_CONTRACT_VERSION
        )

        record[
            "production_confirmation_id"
        ] = confirmation_id

        record[
            "production_confirmation_created_at"
        ] = created_at

        record[
            "production_confirmation_digest"
        ] = confirmation_digest

        record[
            "production_confirmation_actor_subject"
        ] = confirmation.actor_subject

        record[
            "production_confirmation_actor_username"
        ] = confirmation.actor_username

        record[
            "production_confirmation_actor_issuer"
        ] = confirmation.actor_issuer

        record[
            "production_confirmation_actor_azp"
        ] = confirmation.actor_azp

        record[
            "production_confirmation_confirm_object_dn"
        ] = confirmation.confirm_object_dn

        record[
            "production_confirmation_phrase_sha256"
        ] = phrase_sha256

        record[
            "production_confirmation_validated"
        ] = True

        record[
            "production_confirmation_consumed"
        ] = True

        record[
            "production_confirmation_job_creation_authorized"
        ] = False

        record[
            "production_confirmation_runtime_authorized"
        ] = False

        record[
            "production_confirmation_production_authorized"
        ] = False

        record[
            "production_confirmation_ad_write_authorized"
        ] = False

        _atomic_write_registry(
            registry_path,
            registry,
        )

        return AclDelegationProductionConfirmationPersistence(
            contract_version=(
                ACL_DELEGATION_PRODUCTION_CONFIRMATION_PERSISTENCE_CONTRACT_VERSION
            ),
            state=(
                "production_confirmation_dormant"
            ),
            source_state=(
                "prewrite_validated"
            ),

            confirmation_id=confirmation_id,
            confirmation_digest=(
                confirmation_digest
            ),
            confirmation_created_at=(
                created_at
            ),

            claim_id=confirmation.claim_id,
            ticket_id=confirmation.ticket_id,
            execution_id=(
                confirmation.execution_id
            ),

            actor_subject=(
                confirmation.actor_subject
            ),
            actor_username=(
                confirmation.actor_username
            ),

            target_dn=confirmation.target_dn,
            target_object_guid=(
                confirmation.target_object_guid
            ),

            principal_sid=(
                confirmation.principal_sid
            ),

            dacl_sddl_sha256=(
                confirmation.dacl_sddl_sha256
            ),
            acl_fingerprint=(
                confirmation.acl_fingerprint
            ),

            confirmation_validated=True,
            confirmation_consumed=True,

            job_creation_authorized=False,
            runtime_authorized=False,
            production_authorized=False,
            ad_write_authorized=False,
        )


def assert_acl_delegation_production_confirmation_persistence_invariants(
) -> None:
    if not ACL_DELEGATION_PRODUCTION_CONFIRMATION_PERSISTENCE_ENABLED:
        raise RuntimeError(
            "C8.4D-A2C1 persistence must remain enabled"
        )

    if ACL_DELEGATION_PRODUCTION_CONFIRMATION_JOB_CREATION_AUTHORIZED:
        raise RuntimeError(
            "C8.4D-A2C1 job creation must remain disabled"
        )

    if ACL_DELEGATION_PRODUCTION_CONFIRMATION_RUNTIME_AUTHORIZED:
        raise RuntimeError(
            "C8.4D-A2C1 runtime must remain disabled"
        )

    if ACL_DELEGATION_PRODUCTION_CONFIRMATION_PRODUCTION_AUTHORIZED:
        raise RuntimeError(
            "C8.4D-A2C1 Production must remain unauthorized"
        )

    if ACL_DELEGATION_PRODUCTION_CONFIRMATION_AD_WRITE_AUTHORIZED:
        raise RuntimeError(
            "C8.4D-A2C1 AD writes must remain unauthorized"
        )


assert_acl_delegation_production_confirmation_persistence_invariants()
