from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from app.services.acl_delegation_prewrite_ticket import (
    _parse_timestamp,
    _payload_digest,
)
from app.services.acl_delegation_write_replay import (
    AclDelegationWriteReplayStorageError,
    _atomic_write_registry,
    _exclusive_registry_lock,
    _normalize_registry_path,
    _safe_load_registry,
)


ACL_DELEGATION_PREWRITE_RUNTIME_CONTRACT_VERSION = (
    "c8.4c5c"
)

# C8.4C5C1 = machine d'etat uniquement.
# Aucune route agent n'est encore exposee.
ACL_DELEGATION_PREWRITE_AGENT_ENDPOINTS_ENABLED = True

ACL_DELEGATION_PREWRITE_APPLY_ENABLED = False
ACL_DELEGATION_PREWRITE_PRODUCTION_AUTHORIZED = False
ACL_DELEGATION_PREWRITE_AD_WRITE_AUTHORIZED = False


class AclDelegationPrewriteRuntimeError(
    ValueError
):
    pass


class AclDelegationPrewriteRuntimeConflict(
    AclDelegationPrewriteRuntimeError
):
    pass


@dataclass(frozen=True)
class AclDelegationPrewriteExecution:
    contract_version: str
    state: str

    ticket_id: str
    execution_id: str

    claim_id: str
    consumption_id: str

    claimed_at: str
    claimed_by: str
    expires_at: str

    payload_digest: str
    payload: dict

    prewrite_validation_runtime_authorized: bool

    production_authorized: bool
    ad_write_authorized: bool


@dataclass(frozen=True)
class AclDelegationPrewriteCompletion:
    contract_version: str
    state: str

    ticket_id: str
    execution_id: str

    completed_at: str
    success: bool

    prewrite_validation_runtime_authorized: bool

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

    if not isinstance(
        resolved,
        datetime,
    ):
        raise AclDelegationPrewriteRuntimeError(
            "Horodatage runtime ACL invalide"
        )

    if resolved.tzinfo is None:
        raise AclDelegationPrewriteRuntimeError(
            "Horodatage runtime ACL sans fuseau"
        )

    return resolved.astimezone(
        timezone.utc
    )


def _required_string(
    value,
    field_name: str,
) -> str:
    normalized = str(
        value or ""
    ).strip()

    if not normalized:
        raise AclDelegationPrewriteRuntimeError(
            field_name
            + " ACL obligatoire"
        )

    return normalized


def _find_ticket_record(
    registry: dict,
    ticket_id: str,
) -> dict:
    normalized = ticket_id.lower()

    matches = [
        record
        for record in registry["records"]
        if str(
            record.get(
                "prewrite_ticket_id"
            )
            or ""
        ).strip().lower()
        == normalized
    ]

    if not matches:
        raise AclDelegationPrewriteRuntimeError(
            "Ticket ACL pre-write introuvable"
        )

    if len(matches) != 1:
        raise AclDelegationWriteReplayStorageError(
            "Ticket ACL pre-write duplique"
        )

    return matches[0]


def _assert_ticket_integrity(
    record: dict,
) -> None:
    if (
        record.get(
            "prewrite_ticket_contract_version"
        )
        != "c8.4c5a"
    ):
        raise AclDelegationPrewriteRuntimeError(
            "Contrat ticket ACL invalide"
        )

    payload = record.get(
        "prewrite_ticket_payload"
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise AclDelegationWriteReplayStorageError(
            "Payload ticket ACL absent"
        )

    expected_digest = str(
        record.get(
            "prewrite_ticket_payload_digest"
        )
        or ""
    ).strip().lower()

    actual_digest = _payload_digest(
        payload
    )

    if actual_digest != expected_digest:
        raise AclDelegationWriteReplayStorageError(
            "Digest payload ticket ACL invalide"
        )

    authorization = payload.get(
        "authorization"
    )

    if not isinstance(
        authorization,
        dict,
    ):
        raise AclDelegationWriteReplayStorageError(
            "Authorization ticket ACL absente"
        )

    for key in (
        "job_creation_authorized",
        "runtime_authorized",
        "production_authorized",
        "ad_write_authorized",
    ):
        if authorization.get(key) is not False:
            raise AclDelegationWriteReplayStorageError(
                "Autorisation ACL interdite "
                "dans le ticket"
            )

    for key in (
        "job_creation_authorized",
        "runtime_authorized",
        "production_authorized",
        "ad_write_authorized",
    ):
        if record.get(key) is not False:
            raise AclDelegationWriteReplayStorageError(
                "Claim ACL autorisant interdit"
            )


def list_pending_acl_delegation_prewrite_tickets(
    *,
    replay_registry_file: Path,
    now: datetime | None = None,
) -> dict:
    pending_now = _normalize_now(
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

        pending = []

        for record in registry["records"]:
            if (
                record.get("state")
                != "prewrite_ticketed"
            ):
                continue

            _assert_ticket_integrity(
                record
            )

            expires_at = _parse_timestamp(
                record.get(
                    "prewrite_ticket_expires_at"
                ),
                "prewrite_ticket_expires_at",
            )

            if pending_now > expires_at:
                continue

            pending.append({
                "contract_version": (
                    record[
                        "prewrite_ticket_contract_version"
                    ]
                ),
                "state": "prewrite_ticketed",
                "ticket_id": (
                    record[
                        "prewrite_ticket_id"
                    ]
                ),
                "claim_id": (
                    record["claim_id"]
                ),
                "consumption_id": (
                    record["consumption_id"]
                ),
                "created_at": (
                    record[
                        "prewrite_ticket_created_at"
                    ]
                ),
                "expires_at": (
                    record[
                        "prewrite_ticket_expires_at"
                    ]
                ),
                "payload_digest": (
                    record[
                        "prewrite_ticket_payload_digest"
                    ]
                ),
                "authorization": {
                    "prewrite_validation_runtime_authorized": False,
                    "job_creation_authorized": False,
                    "runtime_authorized": False,
                    "production_authorized": False,
                    "ad_write_authorized": False,
                },
            })

        pending.sort(
            key=lambda item: (
                item.get("created_at")
                or ""
            )
        )

        return {
            "count": len(pending),
            "tickets": pending,
        }


def claim_acl_delegation_prewrite_ticket_for_agent(
    *,
    replay_registry_file: Path,
    ticket_id: str,
    agent_name: str,
    now: datetime | None = None,
) -> AclDelegationPrewriteExecution:
    normalized_ticket_id = _required_string(
        ticket_id,
        "ticket_id",
    )

    normalized_agent_name = _required_string(
        agent_name,
        "agent_name",
    )

    claim_now = _normalize_now(
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

        record = _find_ticket_record(
            registry,
            normalized_ticket_id,
        )

        if (
            record.get("state")
            != "prewrite_ticketed"
        ):
            raise AclDelegationPrewriteRuntimeConflict(
                "Ticket ACL pre-write non disponible"
            )

        if (
            record.get(
                "prewrite_validation_runtime_authorized"
            )
            is not False
        ):
            raise AclDelegationWriteReplayStorageError(
                "Runtime ticket ACL deja autorise"
            )

        _assert_ticket_integrity(
            record
        )

        expires_at = _parse_timestamp(
            record.get(
                "prewrite_ticket_expires_at"
            ),
            "prewrite_ticket_expires_at",
        )

        if claim_now > expires_at:
            raise AclDelegationPrewriteRuntimeConflict(
                "Ticket ACL pre-write expire"
            )

        execution_id = str(
            uuid.uuid4()
        )

        claimed_at = (
            claim_now.isoformat()
        )

        record["state"] = (
            "prewrite_processing"
        )

        record[
            "prewrite_validation_runtime_authorized"
        ] = True

        record[
            "prewrite_execution_id"
        ] = execution_id

        record[
            "prewrite_claimed_at"
        ] = claimed_at

        record[
            "prewrite_claimed_by"
        ] = normalized_agent_name

        _atomic_write_registry(
            registry_path,
            registry,
        )

        payload = json.loads(
            json.dumps(
                record[
                    "prewrite_ticket_payload"
                ]
            )
        )

        return AclDelegationPrewriteExecution(
            contract_version=(
                ACL_DELEGATION_PREWRITE_RUNTIME_CONTRACT_VERSION
            ),
            state="prewrite_processing",

            ticket_id=(
                record["prewrite_ticket_id"]
            ),
            execution_id=execution_id,

            claim_id=(
                record["claim_id"]
            ),
            consumption_id=(
                record["consumption_id"]
            ),

            claimed_at=claimed_at,
            claimed_by=normalized_agent_name,
            expires_at=(
                record[
                    "prewrite_ticket_expires_at"
                ]
            ),

            payload_digest=(
                record[
                    "prewrite_ticket_payload_digest"
                ]
            ),
            payload=payload,

            prewrite_validation_runtime_authorized=True,

            production_authorized=False,
            ad_write_authorized=False,
        )


def _validate_success_result(
    *,
    record: dict,
    result: dict,
) -> dict:
    if not isinstance(
        result,
        dict,
    ):
        raise AclDelegationPrewriteRuntimeError(
            "Resultat ACL pre-write invalide"
        )

    exact_values = {
        "action": "prevalidate_acl_delegation",
        "contract_version": "c8.4c1",
        "source_claim_contract_version": "c8.4b4",
        "execution_policy": (
            "prewrite_validation_only"
        ),
        "prewrite_validated": True,
        "object_guid_revalidated": True,
        "dacl_revalidated": True,
        "principal_sid_revalidated": True,
        "write_performed": False,
        "job_creation_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "ad_write_authorized": False,
    }

    for key, expected in exact_values.items():
        if result.get(key) != expected:
            raise AclDelegationPrewriteRuntimeError(
                "Resultat ACL pre-write "
                "incoherent : "
                + key
            )

    target = result.get("target")
    principal = result.get("principal")
    dacl = result.get("dacl")

    if not isinstance(target, dict):
        raise AclDelegationPrewriteRuntimeError(
            "Cible resultat ACL invalide"
        )

    if not isinstance(principal, dict):
        raise AclDelegationPrewriteRuntimeError(
            "Principal resultat ACL invalide"
        )

    if not isinstance(dacl, dict):
        raise AclDelegationPrewriteRuntimeError(
            "DACL resultat ACL invalide"
        )

    if (
        str(
            target.get("object_guid")
            or ""
        ).lower()
        != str(
            record.get(
                "target_object_guid"
            )
            or ""
        ).lower()
    ):
        raise AclDelegationPrewriteRuntimeError(
            "objectGUID resultat ACL incoherent"
        )

    if (
        str(
            principal.get("sid")
            or ""
        ).lower()
        != str(
            record.get("principal_sid")
            or ""
        ).lower()
    ):
        raise AclDelegationPrewriteRuntimeError(
            "SID resultat ACL incoherent"
        )

    if (
        str(
            dacl.get(
                "dacl_sddl_sha256"
            )
            or ""
        ).lower()
        != str(
            record.get(
                "dacl_sddl_sha256"
            )
            or ""
        ).lower()
    ):
        raise AclDelegationPrewriteRuntimeError(
            "SHA DACL resultat incoherent"
        )

    if (
        str(
            dacl.get(
                "acl_fingerprint"
            )
            or ""
        ).lower()
        != str(
            record.get(
                "acl_fingerprint"
            )
            or ""
        ).lower()
    ):
        raise AclDelegationPrewriteRuntimeError(
            "Fingerprint ACL resultat incoherent"
        )

    return {
        "contract_version": "c8.4c1",
        "execution_policy": (
            "prewrite_validation_only"
        ),
        "prewrite_validated": True,
        "object_guid_revalidated": True,
        "dacl_revalidated": True,
        "principal_sid_revalidated": True,
        "target_object_guid": (
            record["target_object_guid"]
        ),
        "principal_sid": (
            record["principal_sid"]
        ),
        "dacl_sddl_sha256": (
            record["dacl_sddl_sha256"]
        ),
        "acl_fingerprint": (
            record["acl_fingerprint"]
        ),
        "write_performed": False,
        "production_authorized": False,
        "ad_write_authorized": False,
    }


def complete_acl_delegation_prewrite_ticket(
    *,
    replay_registry_file: Path,
    ticket_id: str,
    execution_id: str,
    agent_name: str,
    success: bool,
    result: dict | None = None,
    message: str = "",
    now: datetime | None = None,
) -> AclDelegationPrewriteCompletion:
    normalized_ticket_id = _required_string(
        ticket_id,
        "ticket_id",
    )

    normalized_execution_id = _required_string(
        execution_id,
        "execution_id",
    )

    normalized_agent_name = _required_string(
        agent_name,
        "agent_name",
    )

    if success is not True and success is not False:
        raise AclDelegationPrewriteRuntimeError(
            "success ACL doit etre booleen"
        )

    completed_now = _normalize_now(
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

        record = _find_ticket_record(
            registry,
            normalized_ticket_id,
        )

        if (
            record.get("state")
            != "prewrite_processing"
        ):
            raise AclDelegationPrewriteRuntimeConflict(
                "Execution ACL pre-write non disponible"
            )

        if (
            record.get(
                "prewrite_validation_runtime_authorized"
            )
            is not True
        ):
            raise AclDelegationWriteReplayStorageError(
                "Runtime ACL pre-write non autorise"
            )

        if (
            str(
                record.get(
                    "prewrite_execution_id"
                )
                or ""
            )
            != normalized_execution_id
        ):
            raise AclDelegationPrewriteRuntimeConflict(
                "execution_id ACL invalide"
            )

        if (
            str(
                record.get(
                    "prewrite_claimed_by"
                )
                or ""
            )
            != normalized_agent_name
        ):
            raise AclDelegationPrewriteRuntimeConflict(
                "Agent ACL pre-write different"
            )

        _assert_ticket_integrity(
            record
        )

        completed_at = (
            completed_now.isoformat()
        )

        record[
            "prewrite_validation_runtime_authorized"
        ] = False

        record[
            "prewrite_completed_at"
        ] = completed_at

        record[
            "prewrite_success"
        ] = success

        if success:
            summary = _validate_success_result(
                record=record,
                result=result,
            )

            record["state"] = (
                "prewrite_validated"
            )

            record[
                "prewrite_result_summary"
            ] = summary

            record.pop(
                "prewrite_error_message",
                None,
            )

        else:
            error_message = str(
                message or ""
            ).strip()

            if not error_message:
                raise AclDelegationPrewriteRuntimeError(
                    "Message echec ACL obligatoire"
                )

            if len(error_message) > 1024:
                error_message = (
                    error_message[:1024]
                )

            record["state"] = (
                "prewrite_failed"
            )

            record[
                "prewrite_error_message"
            ] = error_message

            record.pop(
                "prewrite_result_summary",
                None,
            )

        _atomic_write_registry(
            registry_path,
            registry,
        )

        return AclDelegationPrewriteCompletion(
            contract_version=(
                ACL_DELEGATION_PREWRITE_RUNTIME_CONTRACT_VERSION
            ),
            state=record["state"],

            ticket_id=(
                record["prewrite_ticket_id"]
            ),
            execution_id=(
                record["prewrite_execution_id"]
            ),

            completed_at=completed_at,
            success=success,

            prewrite_validation_runtime_authorized=False,

            production_authorized=False,
            ad_write_authorized=False,
        )


def assert_acl_delegation_prewrite_runtime_invariants(
) -> None:
    if not ACL_DELEGATION_PREWRITE_AGENT_ENDPOINTS_ENABLED:
        raise RuntimeError(
            "C8.4C5C2 agent endpoints "
            "must remain enabled"
        )

    if ACL_DELEGATION_PREWRITE_APPLY_ENABLED:
        raise RuntimeError(
            "C8.4C5C1 apply ACL "
            "must remain disabled"
        )

    if ACL_DELEGATION_PREWRITE_PRODUCTION_AUTHORIZED:
        raise RuntimeError(
            "C8.4C5C1 Production "
            "must remain unauthorized"
        )

    if ACL_DELEGATION_PREWRITE_AD_WRITE_AUTHORIZED:
        raise RuntimeError(
            "C8.4C5C1 AD writes "
            "must remain unauthorized"
        )


assert_acl_delegation_prewrite_runtime_invariants()
