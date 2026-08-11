from __future__ import annotations

import hashlib
import hmac

from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any, Mapping
from uuid import uuid4

from app.services.ad_deleted_object_restore_authorization_consumption import (
    _canonical_sha256,
    _extract_actor,
    _normalize_now,
    _parse_timestamp,
    _required_sha256,
    _required_string,
    _required_uuid,
)

from app.services.ad_deleted_object_restore_execution_consumption import (
    AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_CONTRACT_VERSION,
    AdDeletedObjectRestoreExecutionConsumption,
    AdDeletedObjectRestoreExecutionConsumptionError,
    assert_ad_deleted_object_restore_execution_consumption_invariants,
)


AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_CONTRACT_VERSION = (
    "c9.5a5e-v1"
)

AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_TTL_SECONDS = 10

AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_SIGNATURE_ALGORITHM = (
    "hmac-sha256"
)

AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_KEY_CONTEXT = (
    "EITAS-C9.5-A5-WINDOWS-EXECUTE-V1"
)

AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_OPERATION = (
    "restore_deleted_object_execute"
)

# R2 remains completely dormant.
AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_ROUTE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_AGENT_ENDPOINT_ENABLED = False
AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_GENERIC_JOB_ENABLED = False
AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_CLAIM_ENABLED = False

# Global EITAS Production remains closed.
AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_RUNTIME_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_PRODUCTION_AUTHORIZED = False

# Narrow capability carried only by a valid signed A5E envelope.
AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_CONTROLLED_RESTORE_AUTHORIZED = True
AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_RESTORE_CMDLET_AUTHORIZED = True
AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_EXECUTION_AUTHORIZED = True

# Set only by the Windows post-execution result, never by this builder.
AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_WRITE_PERFORMED = False


class AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
    ValueError
):
    pass


class AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict(
    AdDeletedObjectRestoreWindowsExecutionEnvelopeError
):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestoreWindowsExecutionEnvelope:
    contract_version: str
    envelope_id: str

    operation: str
    signature_algorithm: str
    key_context: str
    signature: str

    execution_consumption_contract_version: str
    execution_consumption_id: str
    execution_consumption_record_digest: str

    execution_ticket_id: str
    execution_ticket_digest: str

    runtime_gate_id: str
    runtime_gate_digest: str

    authorization_consumption_id: str
    authorization_consumption_record_digest: str

    authorization_id: str
    authorization_digest: str

    preexecution_id: str
    preexecution_digest: str

    object_guid: str
    object_class: str
    class_policy: str
    effective_new_name: str
    effective_target_path: str

    actor_subject: str
    actor_username: str
    actor_issuer: str
    actor_azp: str

    confirmation_sha256: str

    issued_at: str
    expires_at: str

    source_consumption_verified: bool
    source_one_shot_consumed: bool
    human_authorized: bool
    revalidation_passed: bool

    route_enabled: bool
    agent_endpoint_enabled: bool
    generic_job_enabled: bool
    claim_enabled: bool

    runtime_authorized: bool
    production_authorized: bool

    controlled_restore_authorized: bool
    restore_cmdlet_authorized: bool
    execution_authorized: bool

    write_performed: bool


def expected_ad_deleted_object_restore_execution_confirmation(
    source: AdDeletedObjectRestoreExecutionConsumption,
) -> str:
    return (
        "RESTORE "
        + source.object_guid
        + " AS "
        + source.effective_new_name
        + " TO "
        + source.effective_target_path
    )


def _required_signing_secret(
    value: str,
) -> bytes:
    secret = str(
        value or ""
    )

    if len(secret) < 16:
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
            "execution signing secret unavailable or too short"
        )

    return secret.encode(
        "utf-8"
    )


def _derive_execution_signing_key(
    signing_secret: str,
) -> bytes:
    secret = _required_signing_secret(
        signing_secret
    )

    return hmac.new(
        secret,
        AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_KEY_CONTEXT.encode(
            "utf-8"
        ),
        hashlib.sha256,
    ).digest()


def _bool_text(
    value: bool,
) -> str:
    return "true" if value is True else "false"


def build_ad_deleted_object_restore_windows_execution_message(
    envelope: AdDeletedObjectRestoreWindowsExecutionEnvelope,
) -> str:
    fields = (
        ("contract_version", envelope.contract_version),
        ("envelope_id", envelope.envelope_id),
        ("operation", envelope.operation),

        (
            "execution_consumption_contract_version",
            envelope.execution_consumption_contract_version,
        ),
        (
            "execution_consumption_id",
            envelope.execution_consumption_id,
        ),
        (
            "execution_consumption_record_digest",
            envelope.execution_consumption_record_digest,
        ),

        ("execution_ticket_id", envelope.execution_ticket_id),
        ("execution_ticket_digest", envelope.execution_ticket_digest),

        ("runtime_gate_id", envelope.runtime_gate_id),
        ("runtime_gate_digest", envelope.runtime_gate_digest),

        (
            "authorization_consumption_id",
            envelope.authorization_consumption_id,
        ),
        (
            "authorization_consumption_record_digest",
            envelope.authorization_consumption_record_digest,
        ),

        ("authorization_id", envelope.authorization_id),
        ("authorization_digest", envelope.authorization_digest),

        ("preexecution_id", envelope.preexecution_id),
        ("preexecution_digest", envelope.preexecution_digest),

        ("object_guid", envelope.object_guid),
        ("object_class", envelope.object_class),
        ("class_policy", envelope.class_policy),
        ("effective_new_name", envelope.effective_new_name),
        ("effective_target_path", envelope.effective_target_path),

        ("actor_subject", envelope.actor_subject),
        ("actor_username", envelope.actor_username),
        ("actor_issuer", envelope.actor_issuer),
        ("actor_azp", envelope.actor_azp),

        ("confirmation_sha256", envelope.confirmation_sha256),

        ("issued_at", envelope.issued_at),
        ("expires_at", envelope.expires_at),

        (
            "source_consumption_verified",
            _bool_text(envelope.source_consumption_verified),
        ),
        (
            "source_one_shot_consumed",
            _bool_text(envelope.source_one_shot_consumed),
        ),
        (
            "human_authorized",
            _bool_text(envelope.human_authorized),
        ),
        (
            "revalidation_passed",
            _bool_text(envelope.revalidation_passed),
        ),

        (
            "runtime_authorized",
            _bool_text(envelope.runtime_authorized),
        ),
        (
            "production_authorized",
            _bool_text(envelope.production_authorized),
        ),

        (
            "controlled_restore_authorized",
            _bool_text(envelope.controlled_restore_authorized),
        ),
        (
            "restore_cmdlet_authorized",
            _bool_text(envelope.restore_cmdlet_authorized),
        ),
        (
            "execution_authorized",
            _bool_text(envelope.execution_authorized),
        ),

        (
            "write_performed",
            _bool_text(envelope.write_performed),
        ),
    )

    return "\n".join(
        f"{name}={value}"
        for name, value in fields
    )


def sign_ad_deleted_object_restore_windows_execution_envelope(
    envelope: AdDeletedObjectRestoreWindowsExecutionEnvelope,
    *,
    signing_secret: str,
) -> str:
    key = _derive_execution_signing_key(
        signing_secret
    )

    message = (
        build_ad_deleted_object_restore_windows_execution_message(
            envelope
        )
    ).encode(
        "utf-8"
    )

    return hmac.new(
        key,
        message,
        hashlib.sha256,
    ).hexdigest()


def assert_ad_deleted_object_restore_windows_execution_envelope_invariants(
    envelope: AdDeletedObjectRestoreWindowsExecutionEnvelope,
    *,
    signing_secret: str | None = None,
) -> None:
    if (
        envelope.contract_version
        != AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
            "Windows execution contract mismatch"
        )

    if (
        envelope.execution_consumption_contract_version
        != AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
            "execution consumption contract mismatch"
        )

    if (
        envelope.operation
        != AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_OPERATION
    ):
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
            "Windows execution operation mismatch"
        )

    if (
        envelope.signature_algorithm
        != AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_SIGNATURE_ALGORITHM
    ):
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
            "Windows execution signature algorithm mismatch"
        )

    if (
        envelope.key_context
        != AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_KEY_CONTEXT
    ):
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
            "Windows execution key context mismatch"
        )

    for field in (
        "envelope_id",
        "execution_consumption_id",
        "execution_ticket_id",
        "runtime_gate_id",
        "authorization_consumption_id",
        "authorization_id",
        "preexecution_id",
        "object_guid",
    ):
        _required_uuid(
            getattr(
                envelope,
                field,
            ),
            field=field,
        )

    for field in (
        "signature",
        "execution_consumption_record_digest",
        "execution_ticket_digest",
        "runtime_gate_digest",
        "authorization_consumption_record_digest",
        "authorization_digest",
        "preexecution_digest",
        "confirmation_sha256",
    ):
        _required_sha256(
            getattr(
                envelope,
                field,
            ),
            field=field,
        )

    for field in (
        "object_class",
        "class_policy",
        "effective_new_name",
        "effective_target_path",
        "actor_subject",
        "actor_username",
        "actor_issuer",
        "actor_azp",
    ):
        _required_string(
            getattr(
                envelope,
                field,
            ),
            field=field,
        )

    for field in (
        "source_consumption_verified",
        "source_one_shot_consumed",
        "human_authorized",
        "revalidation_passed",
        "controlled_restore_authorized",
        "restore_cmdlet_authorized",
        "execution_authorized",
    ):
        if getattr(
            envelope,
            field,
        ) is not True:
            raise AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
                f"required execution capability absent: {field}"
            )

    for field in (
        "route_enabled",
        "agent_endpoint_enabled",
        "generic_job_enabled",
        "claim_enabled",
        "runtime_authorized",
        "production_authorized",
        "write_performed",
    ):
        if getattr(
            envelope,
            field,
        ) is not False:
            raise AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
                f"unsafe execution envelope flag: {field}"
            )

    issued_at = _parse_timestamp(
        envelope.issued_at,
        field="issued_at",
    )

    expires_at = _parse_timestamp(
        envelope.expires_at,
        field="expires_at",
    )

    if expires_at <= issued_at:
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
            "execution envelope expiration invalid"
        )

    if (
        expires_at - issued_at
        > timedelta(
            seconds=(
                AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_TTL_SECONDS
            )
        )
    ):
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
            "execution envelope TTL exceeds maximum"
        )

    if signing_secret is not None:
        expected = (
            sign_ad_deleted_object_restore_windows_execution_envelope(
                envelope,
                signing_secret=signing_secret,
            )
        )

        if not hmac.compare_digest(
            envelope.signature,
            expected,
        ):
            raise AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
                "Windows execution signature mismatch"
            )


def build_ad_deleted_object_restore_windows_execution_envelope(
    source: AdDeletedObjectRestoreExecutionConsumption,
    *,
    server_actor: Mapping[str, Any],
    signing_secret: str,
    current_mode: str,
    confirmation_text: str,
    now=None,
) -> AdDeletedObjectRestoreWindowsExecutionEnvelope:
    if current_mode != "Simulation":
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
            "controlled restore execution requires Simulation global mode"
        )

    try:
        assert_ad_deleted_object_restore_execution_consumption_invariants(
            source
        )
    except AdDeletedObjectRestoreExecutionConsumptionError as exc:
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeError(
            str(
                exc
            )
        ) from exc

    if source.execution_ticket_consumed is not True:
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict(
            "source execution ticket is not consumed"
        )

    if source.one_shot_consumption is not True:
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict(
            "source one-shot consumption missing"
        )

    if source.human_authorized is not True:
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict(
            "human authorization marker missing"
        )

    if source.revalidation_passed is not True:
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict(
            "revalidation marker missing"
        )

    for field in (
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "restore_whatif_authorized",
        "execution_authorized",
        "write_performed",
    ):
        if getattr(
            source,
            field,
        ) is not False:
            raise AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict(
                f"unsafe source consumption flag: {field}"
            )

    actor = _extract_actor(
        server_actor
    )

    for field, expected in (
        (
            "actor_subject",
            actor["subject"],
        ),
        (
            "actor_username",
            actor["username"],
        ),
        (
            "actor_issuer",
            actor["issuer"],
        ),
        (
            "actor_azp",
            actor["azp"],
        ),
    ):
        if getattr(
            source,
            field,
        ) != expected:
            raise AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict(
                f"actor mismatch: {field}"
            )

    expected_confirmation = (
        expected_ad_deleted_object_restore_execution_confirmation(
            source
        )
    )

    if confirmation_text != expected_confirmation:
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict(
            "controlled restore execution confirmation mismatch"
        )

    confirmation_sha256 = _canonical_sha256(
        {
            "confirmation_text":
                confirmation_text,
        }
    )

    if confirmation_sha256 != source.confirmation_sha256:
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict(
            "controlled restore confirmation digest mismatch"
        )

    current = _normalize_now(
        now
    )

    consumed_at = _parse_timestamp(
        source.consumed_at,
        field="source.consumed_at",
    )

    ticket_expires_at = _parse_timestamp(
        source.execution_ticket_expires_at,
        field="source.execution_ticket_expires_at",
    )

    if current < consumed_at:
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict(
            "execution envelope predates source consumption"
        )

    if current >= ticket_expires_at:
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict(
            "source execution ticket expired before execution envelope"
        )

    expires_at = min(
        current
        + timedelta(
            seconds=(
                AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_TTL_SECONDS
            )
        ),
        ticket_expires_at,
    )

    if expires_at <= current:
        raise AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict(
            "execution envelope has no valid lifetime"
        )

    unsigned = AdDeletedObjectRestoreWindowsExecutionEnvelope(
        contract_version=(
            AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_CONTRACT_VERSION
        ),

        envelope_id=str(
            uuid4()
        ),

        operation=(
            AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_OPERATION
        ),

        signature_algorithm=(
            AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_SIGNATURE_ALGORITHM
        ),

        key_context=(
            AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_KEY_CONTEXT
        ),

        signature="0" * 64,

        execution_consumption_contract_version=(
            source.contract_version
        ),

        execution_consumption_id=(
            source.execution_consumption_id
        ),

        execution_consumption_record_digest=(
            source.record_digest
        ),

        execution_ticket_id=(
            source.execution_ticket_id
        ),

        execution_ticket_digest=(
            source.execution_ticket_digest
        ),

        runtime_gate_id=(
            source.runtime_gate_id
        ),

        runtime_gate_digest=(
            source.runtime_gate_digest
        ),

        authorization_consumption_id=(
            source.authorization_consumption_id
        ),

        authorization_consumption_record_digest=(
            source.authorization_consumption_record_digest
        ),

        authorization_id=(
            source.authorization_id
        ),

        authorization_digest=(
            source.authorization_digest
        ),

        preexecution_id=(
            source.preexecution_id
        ),

        preexecution_digest=(
            source.preexecution_digest
        ),

        object_guid=(
            source.object_guid.lower()
        ),

        object_class=(
            source.object_class
        ),

        class_policy=(
            source.class_policy
        ),

        effective_new_name=(
            source.effective_new_name
        ),

        effective_target_path=(
            source.effective_target_path
        ),

        actor_subject=(
            source.actor_subject
        ),

        actor_username=(
            source.actor_username
        ),

        actor_issuer=(
            source.actor_issuer
        ),

        actor_azp=(
            source.actor_azp
        ),

        confirmation_sha256=(
            source.confirmation_sha256
        ),

        issued_at=current.isoformat(),
        expires_at=expires_at.isoformat(),

        source_consumption_verified=True,
        source_one_shot_consumed=True,
        human_authorized=True,
        revalidation_passed=True,

        route_enabled=False,
        agent_endpoint_enabled=False,
        generic_job_enabled=False,
        claim_enabled=False,

        runtime_authorized=False,
        production_authorized=False,

        controlled_restore_authorized=True,
        restore_cmdlet_authorized=True,
        execution_authorized=True,

        write_performed=False,
    )

    signature = (
        sign_ad_deleted_object_restore_windows_execution_envelope(
            unsigned,
            signing_secret=signing_secret,
        )
    )

    envelope = AdDeletedObjectRestoreWindowsExecutionEnvelope(
        **{
            **asdict(
                unsigned
            ),
            "signature":
                signature,
        }
    )

    assert_ad_deleted_object_restore_windows_execution_envelope_invariants(
        envelope,
        signing_secret=signing_secret,
    )

    return envelope


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_CONTRACT_VERSION",
    "AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_TTL_SECONDS",
    "AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_KEY_CONTEXT",
    "AdDeletedObjectRestoreWindowsExecutionEnvelope",
    "AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict",
    "AdDeletedObjectRestoreWindowsExecutionEnvelopeError",
    "assert_ad_deleted_object_restore_windows_execution_envelope_invariants",
    "build_ad_deleted_object_restore_windows_execution_envelope",
    "build_ad_deleted_object_restore_windows_execution_message",
    "expected_ad_deleted_object_restore_execution_confirmation",
    "sign_ad_deleted_object_restore_windows_execution_envelope",
]
