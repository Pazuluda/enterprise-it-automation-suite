from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.services.acl_delegation_prewrite_runtime import (
    AclDelegationPrewriteRuntimeError,
    _assert_ticket_integrity,
    _find_ticket_record,
)
from app.services.acl_delegation_write_replay import (
    _exclusive_registry_lock,
    _normalize_registry_path,
    _safe_load_registry,
)


ACL_DELEGATION_PREWRITE_STATUS_CONTRACT_VERSION = (
    "c8.4d-a3c3b"
)

ACL_DELEGATION_PREWRITE_STATUS_ENABLED = True

ACL_DELEGATION_PREWRITE_STATUS_PERSISTENCE_ENABLED = False
ACL_DELEGATION_PREWRITE_STATUS_JOB_CREATION_AUTHORIZED = False
ACL_DELEGATION_PREWRITE_STATUS_RUNTIME_AUTHORIZED = False
ACL_DELEGATION_PREWRITE_STATUS_PRODUCTION_AUTHORIZED = False
ACL_DELEGATION_PREWRITE_STATUS_AD_WRITE_AUTHORIZED = False


class AclDelegationPrewriteStatusError(
    ValueError
):
    pass


class AclDelegationPrewriteStatusNotFound(
    AclDelegationPrewriteStatusError
):
    pass


@dataclass(frozen=True)
class AclDelegationPrewriteStatus:
    contract_version: str
    state: str

    ticket_id: str
    claim_id: str
    execution_id: str | None

    created_at: str
    expires_at: str
    claimed_at: str | None
    completed_at: str | None

    success: bool | None

    worker_validation_in_progress: bool
    validation_completed: bool
    confirmation_ready: bool

    job_creation_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    ad_write_authorized: bool


def _clean_string(
    value,
) -> str:
    return str(
        value or ""
    ).strip()


def get_acl_delegation_prewrite_status(
    *,
    replay_registry_file: Path,
    ticket_id: str,
    actor_subject: str,
) -> AclDelegationPrewriteStatus:
    if not ACL_DELEGATION_PREWRITE_STATUS_ENABLED:
        raise AclDelegationPrewriteStatusError(
            "Statut ACL pre-write desactive"
        )

    normalized_ticket_id = _clean_string(
        ticket_id
    )

    normalized_actor_subject = _clean_string(
        actor_subject
    )

    if not normalized_ticket_id:
        raise AclDelegationPrewriteStatusError(
            "ticket_id ACL obligatoire"
        )

    if not normalized_actor_subject:
        raise AclDelegationPrewriteStatusError(
            "Sujet OIDC ACL obligatoire"
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

        try:
            record = _find_ticket_record(
                registry,
                normalized_ticket_id,
            )

        except AclDelegationPrewriteRuntimeError as exc:
            raise AclDelegationPrewriteStatusNotFound(
                "Statut ACL pre-write introuvable"
            ) from exc

        record_actor_subject = _clean_string(
            record.get(
                "actor_subject"
            )
        )

        if (
            not record_actor_subject
            or record_actor_subject
            != normalized_actor_subject
        ):
            # Do not disclose existence of another actor's ticket.
            raise AclDelegationPrewriteStatusNotFound(
                "Statut ACL pre-write introuvable"
            )

        try:
            _assert_ticket_integrity(
                record
            )

        except AclDelegationPrewriteRuntimeError as exc:
            raise AclDelegationPrewriteStatusError(
                str(exc)
            ) from exc

        state = _clean_string(
            record.get("state")
        )

        allowed_states = {
            "prewrite_ticketed",
            "prewrite_processing",
            "prewrite_validated",
            "prewrite_failed",
        }

        if state not in allowed_states:
            raise AclDelegationPrewriteStatusError(
                "Etat ACL pre-write invalide"
            )

        for key in (
            "job_creation_authorized",
            "runtime_authorized",
            "production_authorized",
            "ad_write_authorized",
        ):
            if record.get(key) is not False:
                raise AclDelegationPrewriteStatusError(
                    "Etat ACL pre-write autorisant interdit"
                )

        ticket_record_id = _clean_string(
            record.get(
                "prewrite_ticket_id"
            )
        )

        claim_id = _clean_string(
            record.get(
                "claim_id"
            )
        )

        created_at = _clean_string(
            record.get(
                "prewrite_ticket_created_at"
            )
        )

        expires_at = _clean_string(
            record.get(
                "prewrite_ticket_expires_at"
            )
        )

        if not all((
            ticket_record_id,
            claim_id,
            created_at,
            expires_at,
        )):
            raise AclDelegationPrewriteStatusError(
                "Metadonnees ACL pre-write incompletes"
            )

        execution_id = _clean_string(
            record.get(
                "prewrite_execution_id"
            )
        ) or None

        claimed_at = _clean_string(
            record.get(
                "prewrite_claimed_at"
            )
        ) or None

        completed_at = _clean_string(
            record.get(
                "prewrite_completed_at"
            )
        ) or None

        if state in {
            "prewrite_processing",
            "prewrite_validated",
            "prewrite_failed",
        }:
            if not execution_id:
                raise AclDelegationPrewriteStatusError(
                    "execution_id ACL pre-write absent"
                )

            if not claimed_at:
                raise AclDelegationPrewriteStatusError(
                    "Horodatage claim pre-write absent"
                )

        if state == "prewrite_ticketed":
            if execution_id is not None:
                raise AclDelegationPrewriteStatusError(
                    "execution_id ACL premature"
                )

            success = None

        elif state == "prewrite_processing":
            success = None

        elif state == "prewrite_validated":
            if completed_at is None:
                raise AclDelegationPrewriteStatusError(
                    "Horodatage validation ACL absent"
                )

            if record.get(
                "prewrite_success"
            ) is not True:
                raise AclDelegationPrewriteStatusError(
                    "Succes validation ACL incoherent"
                )

            success = True

        else:
            if completed_at is None:
                raise AclDelegationPrewriteStatusError(
                    "Horodatage echec ACL absent"
                )

            if record.get(
                "prewrite_success"
            ) is not False:
                raise AclDelegationPrewriteStatusError(
                    "Echec validation ACL incoherent"
                )

            success = False

        return AclDelegationPrewriteStatus(
            contract_version=(
                ACL_DELEGATION_PREWRITE_STATUS_CONTRACT_VERSION
            ),

            state=state,

            ticket_id=ticket_record_id,
            claim_id=claim_id,
            execution_id=execution_id,

            created_at=created_at,
            expires_at=expires_at,
            claimed_at=claimed_at,
            completed_at=completed_at,

            success=success,

            worker_validation_in_progress=(
                state == "prewrite_processing"
            ),

            validation_completed=(
                state in {
                    "prewrite_validated",
                    "prewrite_failed",
                }
            ),

            confirmation_ready=(
                state == "prewrite_validated"
            ),

            job_creation_authorized=False,
            runtime_authorized=False,
            production_authorized=False,
            ad_write_authorized=False,
        )


def assert_acl_delegation_prewrite_status_invariants(
) -> None:
    if not ACL_DELEGATION_PREWRITE_STATUS_ENABLED:
        raise RuntimeError(
            "C8.4D-A3C3B status must remain enabled"
        )

    if ACL_DELEGATION_PREWRITE_STATUS_PERSISTENCE_ENABLED:
        raise RuntimeError(
            "C8.4D-A3C3B persistence must remain disabled"
        )

    if ACL_DELEGATION_PREWRITE_STATUS_JOB_CREATION_AUTHORIZED:
        raise RuntimeError(
            "C8.4D-A3C3B job creation must remain disabled"
        )

    if ACL_DELEGATION_PREWRITE_STATUS_RUNTIME_AUTHORIZED:
        raise RuntimeError(
            "C8.4D-A3C3B runtime must remain disabled"
        )

    if ACL_DELEGATION_PREWRITE_STATUS_PRODUCTION_AUTHORIZED:
        raise RuntimeError(
            "C8.4D-A3C3B Production must remain unauthorized"
        )

    if ACL_DELEGATION_PREWRITE_STATUS_AD_WRITE_AUTHORIZED:
        raise RuntimeError(
            "C8.4D-A3C3B AD writes must remain unauthorized"
        )


assert_acl_delegation_prewrite_status_invariants()
