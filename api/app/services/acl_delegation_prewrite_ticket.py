from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path

from app.services.acl_delegation_write_replay import (
    AclDelegationWriteReplayStorageError,
    _atomic_write_registry,
    _exclusive_registry_lock,
    _normalize_registry_path,
    _safe_load_registry,
)


ACL_DELEGATION_PREWRITE_TICKET_CONTRACT_VERSION = (
    "c8.4c5a"
)

ACL_DELEGATION_PREWRITE_TICKET_TTL_SECONDS = 120
ACL_DELEGATION_PREWRITE_CLAIM_MAX_AGE_SECONDS = 300
ACL_DELEGATION_PREWRITE_FUTURE_SKEW_SECONDS = 30

ACL_DELEGATION_PREWRITE_TICKET_ENABLED = True

# C8.4C5A creates only a dormant validation ticket.
ACL_DELEGATION_PREWRITE_RUNTIME_ENABLED = False

# These remain ACL-write authorization flags.
ACL_DELEGATION_PREWRITE_JOB_CREATION_AUTHORIZED = False
ACL_DELEGATION_PREWRITE_PRODUCTION_AUTHORIZED = False
ACL_DELEGATION_PREWRITE_AD_WRITE_AUTHORIZED = False


class AclDelegationPrewriteTicketError(
    ValueError
):
    pass


class AclDelegationPrewriteTicketConflict(
    AclDelegationPrewriteTicketError
):
    pass


@dataclass(frozen=True)
class AclDelegationPrewriteTicket:
    contract_version: str
    state: str

    ticket_id: str
    claim_id: str
    consumption_id: str

    created_at: str
    expires_at: str
    payload_digest: str
    payload: dict

    prewrite_validation_runtime_authorized: bool

    job_creation_authorized: bool
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
        raise AclDelegationPrewriteTicketError(
            "Horodatage ticket ACL invalide"
        )

    if resolved.tzinfo is None:
        raise AclDelegationPrewriteTicketError(
            "Horodatage ticket ACL sans fuseau"
        )

    return resolved.astimezone(
        timezone.utc
    )


def _parse_timestamp(
    value,
    field_name: str,
) -> datetime:
    raw = str(
        value or ""
    ).strip()

    if not raw:
        raise AclDelegationPrewriteTicketError(
            "Horodatage ACL manquant : "
            + field_name
        )

    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(
            raw
        )
    except ValueError as exc:
        raise AclDelegationPrewriteTicketError(
            "Horodatage ACL invalide : "
            + field_name
        ) from exc

    if parsed.tzinfo is None:
        raise AclDelegationPrewriteTicketError(
            "Horodatage ACL sans fuseau : "
            + field_name
        )

    return parsed.astimezone(
        timezone.utc
    )


def _build_payload(
    record: dict,
) -> dict:
    for key in (
        "job_creation_authorized",
        "runtime_authorized",
        "production_authorized",
        "ad_write_authorized",
    ):
        if record.get(key) is not False:
            raise AclDelegationPrewriteTicketError(
                "Claim ACL autorisant interdit"
            )

    if (
        record.get("contract_version_claim")
        != "c8.4b4"
    ):
        raise AclDelegationPrewriteTicketError(
            "Version claim ACL invalide"
        )

    return {
        "contract_version": "c8.4b4",
        "state": "claimed_dormant",

        "claim_id": record["claim_id"],
        "consumption_id": (
            record["consumption_id"]
        ),

        "target": {
            "dn": record["target_dn"],
            "object_guid": (
                record["target_object_guid"]
            ),
        },

        "principal": {
            "dn": record["principal_dn"],
            "sid": record["principal_sid"],
        },

        "ace": {
            "access_control_type": (
                record["access_control_type"]
            ),
            "rights": list(
                record["rights"]
            ),
            "inheritance_type": (
                record["inheritance_type"]
            ),
            "object_type_guid": (
                record.get(
                    "object_type_guid"
                )
            ),
            "inherited_object_type_guid": (
                record.get(
                    "inherited_object_type_guid"
                )
            ),
        },

        "dacl": {
            "dacl_sddl_sha256": (
                record["dacl_sddl_sha256"]
            ),
            "acl_fingerprint": (
                record["acl_fingerprint"]
            ),
        },

        "authorization": {
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    }


def _payload_digest(
    payload: dict,
) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        canonical
    ).hexdigest()


def _ticket_from_record(
    record: dict,
) -> AclDelegationPrewriteTicket:
    return AclDelegationPrewriteTicket(
        contract_version=(
            record[
                "prewrite_ticket_contract_version"
            ]
        ),
        state=record["state"],

        ticket_id=(
            record["prewrite_ticket_id"]
        ),
        claim_id=record["claim_id"],
        consumption_id=(
            record["consumption_id"]
        ),

        created_at=(
            record["prewrite_ticket_created_at"]
        ),
        expires_at=(
            record["prewrite_ticket_expires_at"]
        ),
        payload_digest=(
            record[
                "prewrite_ticket_payload_digest"
            ]
        ),
        payload=dict(
            record["prewrite_ticket_payload"]
        ),

        prewrite_validation_runtime_authorized=(
            record[
                "prewrite_validation_runtime_authorized"
            ]
        ),

        job_creation_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,
    )


def create_acl_delegation_prewrite_ticket(
    *,
    replay_registry_file: Path,
    claim_id: str,
    now: datetime | None = None,
) -> AclDelegationPrewriteTicket:
    if not ACL_DELEGATION_PREWRITE_TICKET_ENABLED:
        raise AclDelegationPrewriteTicketError(
            "Ticket ACL pre-write desactive"
        )

    normalized_claim_id = str(
        claim_id or ""
    ).strip().lower()

    if not normalized_claim_id:
        raise AclDelegationPrewriteTicketError(
            "claim_id ACL obligatoire"
        )

    registry_path = _normalize_registry_path(
        replay_registry_file
    )

    ticket_now = _normalize_now(
        now
    )

    with _exclusive_registry_lock(
        registry_path
    ):
        registry = _safe_load_registry(
            registry_path
        )

        matches = [
            record
            for record in registry["records"]
            if str(
                record.get("claim_id")
                or ""
            ).strip().lower()
            == normalized_claim_id
        ]

        if not matches:
            raise AclDelegationPrewriteTicketError(
                "Claim ACL introuvable"
            )

        if len(matches) != 1:
            raise AclDelegationWriteReplayStorageError(
                "claim_id ACL duplique "
                "dans le registre"
            )

        record = matches[0]

        if record.get("state") == "prewrite_ticketed":
            ticket = _ticket_from_record(
                record
            )

            ticket_expires_at = _parse_timestamp(
                ticket.expires_at,
                "prewrite_ticket_expires_at",
            )

            if ticket_now > ticket_expires_at:
                raise AclDelegationPrewriteTicketConflict(
                    "Ticket ACL pre-write expire"
                )

            return ticket

        if record.get("state") != "claimed_dormant":
            raise AclDelegationPrewriteTicketConflict(
                "Claim ACL non disponible "
                "pour ticket pre-write"
            )

        claimed_at = _parse_timestamp(
            record.get("claimed_at"),
            "claimed_at",
        )

        if (
            claimed_at
            > ticket_now
            + timedelta(
                seconds=(
                    ACL_DELEGATION_PREWRITE_FUTURE_SKEW_SECONDS
                )
            )
        ):
            raise AclDelegationPrewriteTicketError(
                "Claim ACL date dans le futur"
            )

        age_seconds = (
            ticket_now
            - claimed_at
        ).total_seconds()

        if (
            age_seconds
            > ACL_DELEGATION_PREWRITE_CLAIM_MAX_AGE_SECONDS
        ):
            raise AclDelegationPrewriteTicketError(
                "Claim ACL trop ancien "
                "pour pre-write"
            )

        payload = _build_payload(
            record
        )

        payload_digest = _payload_digest(
            payload
        )

        ticket_id = str(
            uuid.uuid4()
        )

        created_at = (
            ticket_now.isoformat()
        )

        expires_at = (
            ticket_now
            + timedelta(
                seconds=(
                    ACL_DELEGATION_PREWRITE_TICKET_TTL_SECONDS
                )
            )
        ).isoformat()

        record["state"] = (
            "prewrite_ticketed"
        )

        record["prewrite_ticket_id"] = (
            ticket_id
        )

        record[
            "prewrite_ticket_contract_version"
        ] = (
            ACL_DELEGATION_PREWRITE_TICKET_CONTRACT_VERSION
        )

        record[
            "prewrite_ticket_created_at"
        ] = created_at

        record[
            "prewrite_ticket_expires_at"
        ] = expires_at

        record[
            "prewrite_ticket_payload_digest"
        ] = payload_digest

        record[
            "prewrite_ticket_payload"
        ] = payload

        # C8.4C5A remains dormant.
        record[
            "prewrite_validation_runtime_authorized"
        ] = False

        _atomic_write_registry(
            registry_path,
            registry,
        )

        return _ticket_from_record(
            record
        )


def assert_acl_delegation_prewrite_ticket_invariants(
) -> None:
    if not ACL_DELEGATION_PREWRITE_TICKET_ENABLED:
        raise RuntimeError(
            "C8.4C5A ticket creation must remain enabled"
        )

    if ACL_DELEGATION_PREWRITE_RUNTIME_ENABLED:
        raise RuntimeError(
            "C8.4C5A runtime must remain disabled"
        )

    if ACL_DELEGATION_PREWRITE_JOB_CREATION_AUTHORIZED:
        raise RuntimeError(
            "C8.4C5A generic job creation "
            "must remain disabled"
        )

    if ACL_DELEGATION_PREWRITE_PRODUCTION_AUTHORIZED:
        raise RuntimeError(
            "C8.4C5A Production authorization "
            "must remain disabled"
        )

    if ACL_DELEGATION_PREWRITE_AD_WRITE_AUTHORIZED:
        raise RuntimeError(
            "C8.4C5A AD writes must remain disabled"
        )


assert_acl_delegation_prewrite_ticket_invariants()
