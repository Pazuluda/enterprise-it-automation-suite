from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping


AD_RECYCLE_BIN_ACTIVATION_INTENT_CONTRACT_VERSION = (
    "c9.3a5b-v1"
)

AD_RECYCLE_BIN_ACTIVATION_INTENT_ENABLED = True

AD_RECYCLE_BIN_ACTIVATION_INTENT_MAX_EVIDENCE_AGE_SECONDS = (
    300
)

AD_RECYCLE_BIN_ACTIVATION_INTENT_FUTURE_SKEW_SECONDS = (
    30
)

AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_ENABLED = False
AD_RECYCLE_BIN_ACTIVATION_INTENT_JOB_CREATION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_INTENT_RUNTIME_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_INTENT_PRODUCTION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_INTENT_ACTIVATION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_INTENT_RESTORE_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_INTENT_WRITE_PERFORMED = False


class AdRecycleBinActivationIntentError(ValueError):
    pass


@dataclass(frozen=True)
class AdRecycleBinActivationIntent:
    contract_version: str
    state: str

    forest_name: str
    root_domain: str
    forest_mode: str

    recycle_bin_enabled: bool
    replication_ready: bool

    evidence_created_at: str
    evidence_sha256: str

    actor_subject: str
    actor_username: str
    actor_issuer: str
    actor_azp: str

    acknowledge_forest_wide: bool
    acknowledge_irreversible: bool
    acknowledge_no_restore: bool

    requested_reason: str

    created_at: str

    persistence_enabled: bool
    job_creation_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    activation_authorized: bool
    restore_authorized: bool
    write_performed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_ALLOWED_PAYLOAD_FIELDS = {
    "forest_name",
    "acknowledge_forest_wide",
    "acknowledge_irreversible",
    "acknowledge_no_restore",
    "requested_reason",
}

_FORBIDDEN_CLIENT_IDENTITY_FIELDS = {
    "created_by",
    "actor",
    "actor_subject",
    "actor_username",
    "actor_issuer",
    "actor_azp",
    "subject",
    "username",
    "issuer",
    "azp",
}


def _clean_string(
    value: Any,
    *,
    field: str,
    required: bool = True,
    max_length: int = 512,
) -> str:
    if value is None:
        if required:
            raise AdRecycleBinActivationIntentError(
                f"{field} is required"
            )
        return ""

    if not isinstance(value, str):
        raise AdRecycleBinActivationIntentError(
            f"{field} must be a string"
        )

    cleaned = value.strip()

    if required and not cleaned:
        raise AdRecycleBinActivationIntentError(
            f"{field} is required"
        )

    if len(cleaned) > max_length:
        raise AdRecycleBinActivationIntentError(
            f"{field} exceeds {max_length} characters"
        )

    if any(
        ord(char) < 32
        for char in cleaned
        if char not in "\t"
    ):
        raise AdRecycleBinActivationIntentError(
            f"{field} contains a forbidden character"
        )

    return cleaned


def _normalize_now(
    now: datetime | None,
) -> datetime:
    value = (
        datetime.now(timezone.utc)
        if now is None
        else now
    )

    if value.tzinfo is None:
        raise AdRecycleBinActivationIntentError(
            "now must be timezone-aware"
        )

    return value.astimezone(
        timezone.utc
    )


def _parse_timestamp(
    value: Any,
    *,
    field: str,
) -> datetime:
    raw = _clean_string(
        value,
        field=field,
        max_length=64,
    )

    normalized = (
        raw[:-1] + "+00:00"
        if raw.endswith("Z")
        else raw
    )

    try:
        parsed = datetime.fromisoformat(
            normalized
        )
    except ValueError as exc:
        raise AdRecycleBinActivationIntentError(
            f"{field} is invalid"
        ) from exc

    if parsed.tzinfo is None:
        raise AdRecycleBinActivationIntentError(
            f"{field} must include a timezone"
        )

    return parsed.astimezone(
        timezone.utc
    )


def _canonical_sha256(
    value: Mapping[str, Any],
) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        serialized
    ).hexdigest()


def build_ad_recycle_bin_activation_intent(
    payload: Mapping[str, Any],
    *,
    current_mode: str,
    server_evidence: Mapping[str, Any],
    server_actor: Mapping[str, Any],
    now: datetime | None = None,
) -> AdRecycleBinActivationIntent:
    if not AD_RECYCLE_BIN_ACTIVATION_INTENT_ENABLED:
        raise AdRecycleBinActivationIntentError(
            "Recycle Bin activation intent is disabled"
        )

    if current_mode != "Simulation":
        raise AdRecycleBinActivationIntentError(
            "Recycle Bin activation intent is available "
            "only in Simulation mode"
        )

    if not isinstance(
        payload,
        Mapping,
    ):
        raise AdRecycleBinActivationIntentError(
            "payload must be a mapping"
        )

    client_fields = set(
        payload.keys()
    )

    forbidden = (
        client_fields
        & _FORBIDDEN_CLIENT_IDENTITY_FIELDS
    )

    if forbidden:
        raise AdRecycleBinActivationIntentError(
            "Client identity fields are forbidden: "
            + ", ".join(
                sorted(forbidden)
            )
        )

    unknown = (
        client_fields
        - _ALLOWED_PAYLOAD_FIELDS
    )

    if unknown:
        raise AdRecycleBinActivationIntentError(
            "Unknown activation intent fields: "
            + ", ".join(
                sorted(unknown)
            )
        )

    current_time = _normalize_now(
        now
    )

    requested_forest = _clean_string(
        payload.get(
            "forest_name"
        ),
        field="forest_name",
        max_length=255,
    )

    forest_name = _clean_string(
        server_evidence.get(
            "forest_name"
        ),
        field="server_evidence.forest_name",
        max_length=255,
    )

    root_domain = _clean_string(
        server_evidence.get(
            "root_domain"
        ),
        field="server_evidence.root_domain",
        max_length=255,
    )

    forest_mode = _clean_string(
        server_evidence.get(
            "forest_mode"
        ),
        field="server_evidence.forest_mode",
        max_length=128,
    )

    if (
        requested_forest.casefold()
        != forest_name.casefold()
    ):
        raise AdRecycleBinActivationIntentError(
            "Requested forest does not match "
            "server evidence"
        )

    recycle_bin_enabled = (
        server_evidence.get(
            "recycle_bin_enabled"
        )
    )

    if recycle_bin_enabled is not False:
        raise AdRecycleBinActivationIntentError(
            "Recycle Bin must still be disabled"
        )

    replication_ready = (
        server_evidence.get(
            "replication_ready"
        )
    )

    if replication_ready is not True:
        raise AdRecycleBinActivationIntentError(
            "Replication readiness is required"
        )

    evidence_time = _parse_timestamp(
        server_evidence.get(
            "evidence_created_at"
        ),
        field=(
            "server_evidence."
            "evidence_created_at"
        ),
    )

    future_delta = (
        evidence_time
        - current_time
    ).total_seconds()

    if (
        future_delta
        > AD_RECYCLE_BIN_ACTIVATION_INTENT_FUTURE_SKEW_SECONDS
    ):
        raise AdRecycleBinActivationIntentError(
            "Server evidence is from the future"
        )

    evidence_age = (
        current_time
        - evidence_time
    ).total_seconds()

    if (
        evidence_age
        > AD_RECYCLE_BIN_ACTIVATION_INTENT_MAX_EVIDENCE_AGE_SECONDS
    ):
        raise AdRecycleBinActivationIntentError(
            "Server evidence is stale"
        )

    acknowledge_forest_wide = (
        payload.get(
            "acknowledge_forest_wide"
        )
    )

    acknowledge_irreversible = (
        payload.get(
            "acknowledge_irreversible"
        )
    )

    acknowledge_no_restore = (
        payload.get(
            "acknowledge_no_restore"
        )
    )

    acknowledgements = {
        "acknowledge_forest_wide":
            acknowledge_forest_wide,
        "acknowledge_irreversible":
            acknowledge_irreversible,
        "acknowledge_no_restore":
            acknowledge_no_restore,
    }

    for field, value in acknowledgements.items():
        if value is not True:
            raise AdRecycleBinActivationIntentError(
                f"{field} must be true"
            )

    requested_reason = _clean_string(
        payload.get(
            "requested_reason"
        ),
        field="requested_reason",
        required=False,
        max_length=512,
    )

    actor_subject = _clean_string(
        server_actor.get(
            "subject"
        ),
        field="server_actor.subject",
        max_length=256,
    )

    actor_username = _clean_string(
        server_actor.get(
            "username"
        ),
        field="server_actor.username",
        max_length=128,
    )

    actor_issuer = _clean_string(
        server_actor.get(
            "issuer"
        ),
        field="server_actor.issuer",
        max_length=512,
    )

    actor_azp = _clean_string(
        server_actor.get(
            "azp"
        ),
        field="server_actor.azp",
        max_length=128,
    )

    evidence_payload = {
        "forest_name":
            forest_name,
        "root_domain":
            root_domain,
        "forest_mode":
            forest_mode,
        "recycle_bin_enabled":
            False,
        "replication_ready":
            True,
        "evidence_created_at":
            evidence_time.isoformat(),
    }

    evidence_sha256 = _canonical_sha256(
        evidence_payload
    )

    return AdRecycleBinActivationIntent(
        contract_version=(
            AD_RECYCLE_BIN_ACTIVATION_INTENT_CONTRACT_VERSION
        ),
        state="activation_intent_dormant",

        forest_name=forest_name,
        root_domain=root_domain,
        forest_mode=forest_mode,

        recycle_bin_enabled=False,
        replication_ready=True,

        evidence_created_at=(
            evidence_time.isoformat()
        ),
        evidence_sha256=(
            evidence_sha256
        ),

        actor_subject=actor_subject,
        actor_username=actor_username,
        actor_issuer=actor_issuer,
        actor_azp=actor_azp,

        acknowledge_forest_wide=True,
        acknowledge_irreversible=True,
        acknowledge_no_restore=True,

        requested_reason=requested_reason,

        created_at=(
            current_time.isoformat()
        ),

        persistence_enabled=False,
        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        activation_authorized=False,
        restore_authorized=False,
        write_performed=False,
    )


def assert_ad_recycle_bin_activation_intent_invariants(
    intent: AdRecycleBinActivationIntent,
) -> None:
    if (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_ENABLED
    ):
        raise AdRecycleBinActivationIntentError(
            "C9.3 persistence must remain disabled"
        )

    if (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_JOB_CREATION_AUTHORIZED
    ):
        raise AdRecycleBinActivationIntentError(
            "C9.3 job creation must remain forbidden"
        )

    if (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_RUNTIME_AUTHORIZED
    ):
        raise AdRecycleBinActivationIntentError(
            "C9.3 runtime must remain forbidden"
        )

    if (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_PRODUCTION_AUTHORIZED
    ):
        raise AdRecycleBinActivationIntentError(
            "C9.3 Production must remain forbidden"
        )

    if (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_ACTIVATION_AUTHORIZED
    ):
        raise AdRecycleBinActivationIntentError(
            "C9.3 activation must remain forbidden"
        )

    if (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_RESTORE_AUTHORIZED
    ):
        raise AdRecycleBinActivationIntentError(
            "C9.3 restore must remain forbidden"
        )

    if (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_WRITE_PERFORMED
    ):
        raise AdRecycleBinActivationIntentError(
            "C9.3 write_performed must remain false"
        )

    flags = (
        intent.persistence_enabled,
        intent.job_creation_authorized,
        intent.runtime_authorized,
        intent.production_authorized,
        intent.activation_authorized,
        intent.restore_authorized,
        intent.write_performed,
    )

    if any(flags):
        raise AdRecycleBinActivationIntentError(
            "Dormant activation intent contains "
            "an unsafe authorization flag"
        )


__all__ = [
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_CONTRACT_VERSION",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_ENABLED",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_MAX_EVIDENCE_AGE_SECONDS",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_FUTURE_SKEW_SECONDS",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_ENABLED",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_JOB_CREATION_AUTHORIZED",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_RUNTIME_AUTHORIZED",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_PRODUCTION_AUTHORIZED",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_ACTIVATION_AUTHORIZED",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_RESTORE_AUTHORIZED",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_WRITE_PERFORMED",
    "AdRecycleBinActivationIntent",
    "AdRecycleBinActivationIntentError",
    "build_ad_recycle_bin_activation_intent",
    "assert_ad_recycle_bin_activation_intent_invariants",
]
