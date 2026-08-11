from __future__ import annotations

import hashlib
import hmac

from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import uuid4

from app.services.ad_deleted_object_restore_authorization_consumption import (
    _normalize_now,
    _parse_timestamp,
    _required_sha256,
    _required_string,
    _required_uuid,
)
from app.services.ad_deleted_object_restore_execution_ticket import (
    AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_CONTRACT_VERSION,
    AdDeletedObjectRestoreExecutionTicket,
    AdDeletedObjectRestoreExecutionTicketError,
    assert_ad_deleted_object_restore_execution_ticket_invariants,
)


AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_CONTRACT_VERSION = (
    "c9.5a5c-v1"
)

AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_TTL_SECONDS = 15

AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_SIGNATURE_ALGORITHM = (
    "hmac-sha256"
)

AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_KEY_CONTEXT = (
    "EITAS-C9.5-A5-WINDOWS-WHATIF-V1"
)

AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_OPERATION = (
    "restore_deleted_object_whatif"
)

AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_ROUTE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_AGENT_ENDPOINT_ENABLED = False
AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_JOB_CREATION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_CLAIM_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_RUNTIME_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_PRODUCTION_AUTHORIZED = False

AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_CMDLET_AUTHORIZED = True
AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_AUTHORIZED = True

AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_WINDOWS_WRITE_PERFORMED = False


class AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
    ValueError
):
    pass


class AdDeletedObjectRestoreWindowsWhatIfEnvelopeConflict(
    AdDeletedObjectRestoreWindowsWhatIfEnvelopeError
):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestoreWindowsWhatIfEnvelope:
    contract_version: str
    envelope_id: str

    operation: str
    signature_algorithm: str
    key_context: str
    signature: str

    execution_ticket_contract_version: str
    execution_ticket_id: str
    execution_ticket_digest: str

    runtime_gate_id: str
    runtime_gate_digest: str

    authorization_consumption_id: str
    authorization_id: str
    preexecution_id: str

    object_guid: str
    object_class: str
    class_policy: str
    effective_new_name: str
    effective_target_path: str

    confirmation_sha256: str

    issued_at: str
    expires_at: str

    one_shot_required: bool
    source_ticket_consumed: bool

    route_enabled: bool
    agent_endpoint_enabled: bool
    job_creation_authorized: bool
    claim_authorized: bool
    runtime_authorized: bool
    production_authorized: bool

    restore_cmdlet_authorized: bool
    restore_whatif_authorized: bool

    execution_authorized: bool
    write_performed: bool


def _required_signing_secret(
    value: str,
) -> bytes:
    secret = str(
        value or ""
    )

    if len(secret) < 16:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            "signing secret is unavailable or too short"
        )

    return secret.encode(
        "utf-8"
    )


def _derive_signing_key(
    signing_secret: str,
) -> bytes:
    secret = _required_signing_secret(
        signing_secret
    )

    return hmac.new(
        secret,
        AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_KEY_CONTEXT.encode(
            "utf-8"
        ),
        hashlib.sha256,
    ).digest()


def _bool_text(
    value: bool,
) -> str:
    return (
        "true"
        if value is True
        else "false"
    )


def build_ad_deleted_object_restore_windows_whatif_message(
    envelope: AdDeletedObjectRestoreWindowsWhatIfEnvelope,
) -> str:
    fields = (
        ("contract_version", envelope.contract_version),
        ("envelope_id", envelope.envelope_id),
        ("operation", envelope.operation),
        (
            "execution_ticket_contract_version",
            envelope.execution_ticket_contract_version,
        ),
        ("execution_ticket_id", envelope.execution_ticket_id),
        ("execution_ticket_digest", envelope.execution_ticket_digest),
        ("runtime_gate_id", envelope.runtime_gate_id),
        ("runtime_gate_digest", envelope.runtime_gate_digest),
        (
            "authorization_consumption_id",
            envelope.authorization_consumption_id,
        ),
        ("authorization_id", envelope.authorization_id),
        ("preexecution_id", envelope.preexecution_id),
        ("object_guid", envelope.object_guid),
        ("object_class", envelope.object_class),
        ("class_policy", envelope.class_policy),
        ("effective_new_name", envelope.effective_new_name),
        ("effective_target_path", envelope.effective_target_path),
        ("confirmation_sha256", envelope.confirmation_sha256),
        ("issued_at", envelope.issued_at),
        ("expires_at", envelope.expires_at),
        (
            "one_shot_required",
            _bool_text(envelope.one_shot_required),
        ),
        (
            "source_ticket_consumed",
            _bool_text(envelope.source_ticket_consumed),
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
            "restore_cmdlet_authorized",
            _bool_text(envelope.restore_cmdlet_authorized),
        ),
        (
            "restore_whatif_authorized",
            _bool_text(envelope.restore_whatif_authorized),
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


def sign_ad_deleted_object_restore_windows_whatif_envelope(
    envelope: AdDeletedObjectRestoreWindowsWhatIfEnvelope,
    *,
    signing_secret: str,
) -> str:
    key = _derive_signing_key(
        signing_secret
    )

    message = (
        build_ad_deleted_object_restore_windows_whatif_message(
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


def assert_ad_deleted_object_restore_windows_whatif_envelope_invariants(
    envelope: AdDeletedObjectRestoreWindowsWhatIfEnvelope,
    *,
    signing_secret: str | None = None,
) -> None:
    if (
        envelope.contract_version
        != AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            "Windows WhatIf contract mismatch"
        )

    if (
        envelope.execution_ticket_contract_version
        != AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            "execution ticket contract mismatch"
        )

    if (
        envelope.operation
        != AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_OPERATION
    ):
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            "Windows WhatIf operation mismatch"
        )

    if (
        envelope.signature_algorithm
        != AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_SIGNATURE_ALGORITHM
    ):
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            "signature algorithm mismatch"
        )

    if (
        envelope.key_context
        != AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_KEY_CONTEXT
    ):
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            "signature key context mismatch"
        )

    for field in (
        "envelope_id",
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
        "execution_ticket_digest",
        "runtime_gate_digest",
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
    ):
        _required_string(
            getattr(
                envelope,
                field,
            ),
            field=field,
        )

    if envelope.one_shot_required is not True:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            "one-shot marker must remain true"
        )

    if envelope.source_ticket_consumed is not False:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            "source execution ticket must remain unconsumed"
        )

    for field in (
        "route_enabled",
        "agent_endpoint_enabled",
        "job_creation_authorized",
        "claim_authorized",
        "runtime_authorized",
        "production_authorized",
        "execution_authorized",
        "write_performed",
    ):
        if getattr(
            envelope,
            field,
        ) is not False:
            raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
                f"unsafe Windows WhatIf flag: {field}"
            )

    if envelope.restore_cmdlet_authorized is not True:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            "Restore-ADObject WhatIf capability missing"
        )

    if envelope.restore_whatif_authorized is not True:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            "WhatIf authorization missing"
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
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            "Windows WhatIf expiration invalid"
        )

    if (
        expires_at - issued_at
        > timedelta(
            seconds=(
                AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_TTL_SECONDS
            )
        )
    ):
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            "Windows WhatIf TTL exceeds maximum"
        )

    if signing_secret is not None:
        expected = (
            sign_ad_deleted_object_restore_windows_whatif_envelope(
                envelope,
                signing_secret=signing_secret,
            )
        )

        if not hmac.compare_digest(
            envelope.signature,
            expected,
        ):
            raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
                "Windows WhatIf signature mismatch"
            )


def build_ad_deleted_object_restore_windows_whatif_envelope(
    execution_ticket: AdDeletedObjectRestoreExecutionTicket,
    *,
    signing_secret: str,
    current_mode: str,
    now=None,
) -> AdDeletedObjectRestoreWindowsWhatIfEnvelope:
    if current_mode != "Simulation":
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            "Windows WhatIf envelope requires Simulation global mode"
        )

    try:
        assert_ad_deleted_object_restore_execution_ticket_invariants(
            execution_ticket
        )
    except AdDeletedObjectRestoreExecutionTicketError as exc:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeError(
            str(
                exc
            )
        ) from exc

    if execution_ticket.consumed is not False:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeConflict(
            "execution ticket is already consumed"
        )

    if execution_ticket.one_shot_required is not True:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeConflict(
            "execution ticket is not one-shot"
        )

    if execution_ticket.controlled_restore_authorized is not True:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeConflict(
            "controlled restore capability missing"
        )

    if execution_ticket.restore_cmdlet_authorized is not True:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeConflict(
            "restore cmdlet capability missing"
        )

    if execution_ticket.restore_whatif_authorized is not True:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeConflict(
            "restore WhatIf capability missing"
        )

    if execution_ticket.execution_authorized is not True:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeConflict(
            "source execution capability missing"
        )

    if execution_ticket.runtime_authorized is not False:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeConflict(
            "generic runtime must remain closed"
        )

    if execution_ticket.production_authorized is not False:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeConflict(
            "Production must remain closed"
        )

    current = _normalize_now(
        now
    )

    ticket_expires_at = _parse_timestamp(
        execution_ticket.expires_at,
        field="execution_ticket.expires_at",
    )

    if current >= ticket_expires_at:
        raise AdDeletedObjectRestoreWindowsWhatIfEnvelopeConflict(
            "execution ticket expired before WhatIf envelope creation"
        )

    expires_at = min(
        current
        + timedelta(
            seconds=(
                AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_TTL_SECONDS
            )
        ),
        ticket_expires_at,
    )

    unsigned = AdDeletedObjectRestoreWindowsWhatIfEnvelope(
        contract_version=(
            AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_CONTRACT_VERSION
        ),
        envelope_id=str(
            uuid4()
        ),

        operation=(
            AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_OPERATION
        ),
        signature_algorithm=(
            AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_SIGNATURE_ALGORITHM
        ),
        key_context=(
            AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_KEY_CONTEXT
        ),
        signature="0" * 64,

        execution_ticket_contract_version=(
            execution_ticket.contract_version
        ),
        execution_ticket_id=(
            execution_ticket.execution_ticket_id
        ),
        execution_ticket_digest=(
            execution_ticket.execution_ticket_digest
        ),

        runtime_gate_id=(
            execution_ticket.runtime_gate_id
        ),
        runtime_gate_digest=(
            execution_ticket.runtime_gate_digest
        ),

        authorization_consumption_id=(
            execution_ticket.authorization_consumption_id
        ),
        authorization_id=(
            execution_ticket.authorization_id
        ),
        preexecution_id=(
            execution_ticket.preexecution_id
        ),

        object_guid=(
            execution_ticket.object_guid.lower()
        ),
        object_class=(
            execution_ticket.object_class
        ),
        class_policy=(
            execution_ticket.class_policy
        ),
        effective_new_name=(
            execution_ticket.effective_new_name
        ),
        effective_target_path=(
            execution_ticket.effective_target_path
        ),

        confirmation_sha256=(
            execution_ticket.confirmation_sha256
        ),

        issued_at=current.isoformat(),
        expires_at=expires_at.isoformat(),

        one_shot_required=True,
        source_ticket_consumed=False,

        route_enabled=False,
        agent_endpoint_enabled=False,
        job_creation_authorized=False,
        claim_authorized=False,
        runtime_authorized=False,
        production_authorized=False,

        restore_cmdlet_authorized=True,
        restore_whatif_authorized=True,

        execution_authorized=False,
        write_performed=False,
    )

    signature = (
        sign_ad_deleted_object_restore_windows_whatif_envelope(
            unsigned,
            signing_secret=signing_secret,
        )
    )

    envelope = AdDeletedObjectRestoreWindowsWhatIfEnvelope(
        **{
            **unsigned.__dict__,
            "signature": signature,
        }
    )

    assert_ad_deleted_object_restore_windows_whatif_envelope_invariants(
        envelope,
        signing_secret=signing_secret,
    )

    return envelope


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_CONTRACT_VERSION",
    "AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_TTL_SECONDS",
    "AD_DELETED_OBJECT_RESTORE_WINDOWS_WHATIF_KEY_CONTEXT",
    "AdDeletedObjectRestoreWindowsWhatIfEnvelope",
    "AdDeletedObjectRestoreWindowsWhatIfEnvelopeConflict",
    "AdDeletedObjectRestoreWindowsWhatIfEnvelopeError",
    "assert_ad_deleted_object_restore_windows_whatif_envelope_invariants",
    "build_ad_deleted_object_restore_windows_whatif_envelope",
    "build_ad_deleted_object_restore_windows_whatif_message",
    "sign_ad_deleted_object_restore_windows_whatif_envelope",
]
