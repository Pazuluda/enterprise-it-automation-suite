from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from app.core.security import (
    AuthenticatedIdentity,
    OIDC_ALLOWED_AZP,
    OIDC_ISSUER,
)

from app.services.ad_recycle_bin_activation_intent import (
    AdRecycleBinActivationIntentError,
    build_ad_recycle_bin_activation_intent,
)

from app.services.ad_recycle_bin_activation_intent_persistence import (
    AdRecycleBinActivationIntentPersistenceError,
    persist_ad_recycle_bin_activation_intent,
)


AD_RECYCLE_BIN_ACTIVATION_PREPARE_CONTRACT_VERSION = (
    "c9.3a5d-a4-v1"
)

AD_RECYCLE_BIN_ACTIVATION_PREPARE_ENABLED = True

AD_RECYCLE_BIN_ACTIVATION_PREPARE_RUNTIME_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_PREPARE_PRODUCTION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_PREPARE_ACTIVATION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_PREPARE_RESTORE_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_PREPARE_WRITE_PERFORMED = False

_ALLOWED_CLIENT_FIELDS = {
    "evidence_job_id",
    "forest_name",
    "acknowledge_forest_wide",
    "acknowledge_irreversible",
    "acknowledge_no_restore",
    "requested_reason",
}

_REQUIRED_ROLES = frozenset(
    {
        "ADAdmin",
        "UltraAdmin",
    }
)


class AdRecycleBinActivationPrepareError(
    ValueError
):
    pass


def _clean(
    value: Any,
    *,
    field: str,
    max_length: int,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise AdRecycleBinActivationPrepareError(
            f"{field} must be a string"
        )

    cleaned = value.strip()

    if not cleaned:
        raise AdRecycleBinActivationPrepareError(
            f"{field} is required"
        )

    if len(cleaned) > max_length:
        raise AdRecycleBinActivationPrepareError(
            f"{field} exceeds {max_length} characters"
        )

    return cleaned


def _load_jobs(
    jobs_file: Path,
) -> list[dict[str, Any]]:
    try:
        data = json.loads(
            jobs_file.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise AdRecycleBinActivationPrepareError(
            "Unable to read AD Explorer evidence storage"
        ) from exc

    if not isinstance(
        data,
        list,
    ):
        raise AdRecycleBinActivationPrepareError(
            "AD Explorer evidence storage is invalid"
        )

    return [
        item
        for item in data
        if isinstance(
            item,
            dict,
        )
    ]


def _authoritative_actor(
    identity: AuthenticatedIdentity,
) -> dict[str, str]:
    if not isinstance(
        identity,
        AuthenticatedIdentity,
    ):
        raise AdRecycleBinActivationPrepareError(
            "Authenticated OIDC identity is required"
        )

    if identity.auth_type != "oidc":
        raise AdRecycleBinActivationPrepareError(
            "OIDC authentication is required"
        )

    if identity.roles.isdisjoint(
        _REQUIRED_ROLES
    ):
        raise AdRecycleBinActivationPrepareError(
            "ADAdmin or UltraAdmin role is required"
        )

    subject = _clean(
        identity.subject,
        field="identity.subject",
        max_length=256,
    )

    username = _clean(
        identity.username,
        field="identity.username",
        max_length=128,
    )

    claims = identity.claims

    if not isinstance(
        claims,
        dict,
    ):
        raise AdRecycleBinActivationPrepareError(
            "OIDC claims are invalid"
        )

    claim_subject = _clean(
        claims.get("sub"),
        field="identity.claims.sub",
        max_length=256,
    )

    if claim_subject != subject:
        raise AdRecycleBinActivationPrepareError(
            "OIDC subject mismatch"
        )

    issuer = _clean(
        claims.get("iss"),
        field="identity.claims.iss",
        max_length=512,
    )

    if issuer != OIDC_ISSUER:
        raise AdRecycleBinActivationPrepareError(
            "OIDC issuer mismatch"
        )

    azp = _clean(
        claims.get("azp"),
        field="identity.claims.azp",
        max_length=128,
    )

    if (
        OIDC_ALLOWED_AZP
        and azp not in OIDC_ALLOWED_AZP
    ):
        raise AdRecycleBinActivationPrepareError(
            "OIDC azp is not allowed"
        )

    return {
        "subject":
            subject,

        "username":
            username,

        "issuer":
            issuer,

        "azp":
            azp,
    }


def _resolve_server_evidence(
    jobs_file: Path,
    *,
    evidence_job_id: str,
) -> dict[str, Any]:
    jobs = _load_jobs(
        jobs_file
    )

    matches = [
        job
        for job in jobs
        if str(
            job.get("id")
            or ""
        ).strip() == evidence_job_id
    ]

    if len(matches) != 1:
        raise AdRecycleBinActivationPrepareError(
            "Evidence job not found or ambiguous"
        )

    job = matches[0]

    if (
        job.get("type")
        != "ad_explorer"
    ):
        raise AdRecycleBinActivationPrepareError(
            "Evidence job type is invalid"
        )

    if (
        job.get("action")
        != "get_recycle_bin_activation_evidence"
    ):
        raise AdRecycleBinActivationPrepareError(
            "Evidence job action is invalid"
        )

    if (
        job.get("status")
        != "completed"
    ):
        raise AdRecycleBinActivationPrepareError(
            "Evidence job is not completed"
        )

    if (
        job.get("success")
        is not True
    ):
        raise AdRecycleBinActivationPrepareError(
            "Evidence job did not succeed"
        )

    result = job.get(
        "result"
    )

    if not isinstance(
        result,
        dict,
    ):
        raise AdRecycleBinActivationPrepareError(
            "Evidence result is invalid"
        )

    required_false = (
        "activation_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "write_performed",
    )

    if (
        result.get("read_only")
        is not True
    ):
        raise AdRecycleBinActivationPrepareError(
            "Evidence result is not read-only"
        )

    for field in required_false:
        if result.get(field) is not False:
            raise AdRecycleBinActivationPrepareError(
                f"Unsafe evidence flag: {field}"
            )

    if (
        result.get("recycle_bin_enabled")
        is not False
    ):
        raise AdRecycleBinActivationPrepareError(
            "Recycle Bin must still be disabled"
        )

    if (
        result.get("replication_ready")
        is not True
    ):
        raise AdRecycleBinActivationPrepareError(
            "Replication is not ready"
        )

    if (
        result.get(
            "replication_query_succeeded"
        )
        is not True
    ):
        raise AdRecycleBinActivationPrepareError(
            "Replication query did not succeed"
        )

    if (
        result.get(
            "replication_partner_query_succeeded"
        )
        is not True
    ):
        raise AdRecycleBinActivationPrepareError(
            "Replication partner query did not succeed"
        )

    if (
        int(
            result.get(
                "replication_failure_count"
            )
            or 0
        )
        != 0
    ):
        raise AdRecycleBinActivationPrepareError(
            "Replication failures are present"
        )

    return {
        "forest_name":
            result.get(
                "forest_name"
            ),

        "root_domain":
            result.get(
                "root_domain"
            ),

        "forest_mode":
            result.get(
                "forest_mode"
            ),

        "recycle_bin_enabled":
            False,

        "replication_ready":
            True,

        "evidence_created_at":
            result.get(
                "evidence_created_at"
            ),
    }


def prepare_ad_recycle_bin_activation_intent(
    jobs_file: Path,
    storage_file: Path,
    payload: Mapping[str, Any],
    *,
    identity: AuthenticatedIdentity,
    current_mode: str,
    now: datetime | None = None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    if not AD_RECYCLE_BIN_ACTIVATION_PREPARE_ENABLED:
        raise AdRecycleBinActivationPrepareError(
            "Activation preparation is disabled"
        )

    if current_mode != "Simulation":
        raise AdRecycleBinActivationPrepareError(
            "Activation preparation is available only in Simulation mode"
        )

    if not isinstance(
        payload,
        Mapping,
    ):
        raise AdRecycleBinActivationPrepareError(
            "payload must be a mapping"
        )

    unknown = (
        set(payload.keys())
        - _ALLOWED_CLIENT_FIELDS
    )

    if unknown:
        raise AdRecycleBinActivationPrepareError(
            "Unknown preparation fields: "
            + ", ".join(
                sorted(unknown)
            )
        )

    evidence_job_id = _clean(
        payload.get(
            "evidence_job_id"
        ),
        field="evidence_job_id",
        max_length=128,
    )

    actor = _authoritative_actor(
        identity
    )

    server_evidence = _resolve_server_evidence(
        jobs_file,
        evidence_job_id=evidence_job_id,
    )

    intent_payload = {
        "forest_name":
            payload.get(
                "forest_name"
            ),

        "acknowledge_forest_wide":
            payload.get(
                "acknowledge_forest_wide"
            ),

        "acknowledge_irreversible":
            payload.get(
                "acknowledge_irreversible"
            ),

        "acknowledge_no_restore":
            payload.get(
                "acknowledge_no_restore"
            ),

        "requested_reason":
            payload.get(
                "requested_reason"
            ),
    }

    try:
        intent = build_ad_recycle_bin_activation_intent(
            intent_payload,
            current_mode=current_mode,
            server_evidence=server_evidence,
            server_actor=actor,
            now=now,
        )

        persisted = persist_ad_recycle_bin_activation_intent(
            intent,
            storage_file=storage_file,
            now=now,
        )

    except (
        AdRecycleBinActivationIntentError,
        AdRecycleBinActivationIntentPersistenceError,
    ) as exc:
        raise AdRecycleBinActivationPrepareError(
            str(exc)
        ) from exc

    response = {
        "message":
            "Intention d'activation de la Corbeille "
            "préparée en état dormant.",

        "contract_version":
            AD_RECYCLE_BIN_ACTIVATION_PREPARE_CONTRACT_VERSION,

        "state":
            persisted.state,

        "status":
            persisted.status,

        "intent_id":
            persisted.intent_id,

        "intent_digest":
            persisted.intent_digest,

        "evidence_job_id":
            evidence_job_id,

        "evidence_sha256":
            persisted.evidence_sha256,

        "forest_name":
            persisted.forest_name,

        "root_domain":
            persisted.root_domain,

        "actor_subject":
            persisted.actor_subject,

        "actor_username":
            persisted.actor_username,

        "activation_authorized":
            False,

        "runtime_authorized":
            False,

        "production_authorized":
            False,

        "restore_authorized":
            False,

        "write_performed":
            False,
    }

    audit_event = {
        "action":
            "ad_recycle_bin_activation_intent_prepared",

        "request_id":
            persisted.intent_id,

        "actor":
            persisted.actor_username,

        "message":
            "Intention d'activation Corbeille AD "
            "préparée en état dormant",

        "details": {
            "intent_id":
                persisted.intent_id,

            "evidence_job_id":
                evidence_job_id,

            "forest_name":
                persisted.forest_name,

            "state":
                persisted.state,

            "status":
                persisted.status,

            "activation_authorized":
                False,

            "production_authorized":
                False,

            "restore_authorized":
                False,

            "write_performed":
                False,
        },
    }

    return (
        response,
        audit_event,
    )


__all__ = [
    "AD_RECYCLE_BIN_ACTIVATION_PREPARE_CONTRACT_VERSION",
    "AdRecycleBinActivationPrepareError",
    "prepare_ad_recycle_bin_activation_intent",
]
