from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path

from app.core.security import (
    AuthenticatedIdentity,
    OIDC_ALLOWED_AZP,
    OIDC_ISSUER,
)

from app.services.acl_delegation_write_intent import (
    ACL_DELEGATION_WRITE_CONFIRMATION_PHRASE,
)
from app.services.acl_delegation_write_replay import (
    AclDelegationWriteReplayStorageError,
    _exclusive_registry_lock,
    _normalize_registry_path,
    _safe_load_registry,
)


ACL_DELEGATION_PRODUCTION_CONFIRMATION_CONTRACT_VERSION = (
    "c8.4d-a2b"
)

ACL_DELEGATION_PRODUCTION_CONFIRMATION_MAX_AGE_SECONDS = (
    120
)

ACL_DELEGATION_PRODUCTION_CONFIRMATION_FUTURE_SKEW_SECONDS = (
    30
)

ACL_DELEGATION_PRODUCTION_CONFIRMATION_ENABLED = True

# C8.4D-A2B validates a final human confirmation only.
# It does not persist an executable authorization and does not
# expose any runtime or Active Directory write path.
ACL_DELEGATION_PRODUCTION_CONFIRMATION_PERSISTENCE_ENABLED = (
    False
)
ACL_DELEGATION_PRODUCTION_CONFIRMATION_JOB_CREATION_AUTHORIZED = (
    False
)
ACL_DELEGATION_PRODUCTION_CONFIRMATION_RUNTIME_AUTHORIZED = (
    False
)
ACL_DELEGATION_PRODUCTION_CONFIRMATION_PRODUCTION_AUTHORIZED = (
    False
)
ACL_DELEGATION_PRODUCTION_CONFIRMATION_AD_WRITE_AUTHORIZED = (
    False
)


class AclDelegationProductionConfirmationError(
    ValueError
):
    pass


class AclDelegationProductionConfirmationConflict(
    AclDelegationProductionConfirmationError
):
    pass


@dataclass(frozen=True)
class AclDelegationProductionConfirmation:
    contract_version: str
    state: str

    confirmation_validated: bool

    claim_id: str
    ticket_id: str
    execution_id: str

    actor_subject: str
    actor_username: str
    actor_roles: tuple[str, ...]
    actor_issuer: str
    actor_azp: str

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

    prewrite_completed_at: str

    confirm_object_dn: str
    confirmation_phrase: str

    job_creation_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    ad_write_authorized: bool


def _clean_string(value) -> str:
    return str(
        value or ""
    ).strip()


def _required_string(
    value,
    field_name: str,
) -> str:
    normalized = _clean_string(
        value
    )

    if not normalized:
        raise AclDelegationProductionConfirmationError(
            field_name
            + " ACL obligatoire"
        )

    return normalized


def _normalize_now(
    now: datetime | None,
) -> datetime:
    resolved = (
        now
        if now is not None
        else datetime.now(
            timezone.utc
        )
    )

    if not isinstance(
        resolved,
        datetime,
    ):
        raise AclDelegationProductionConfirmationError(
            "Horodatage confirmation ACL invalide"
        )

    if resolved.tzinfo is None:
        raise AclDelegationProductionConfirmationError(
            "Horodatage confirmation ACL sans fuseau"
        )

    return resolved.astimezone(
        timezone.utc
    )


def _parse_timestamp(
    value,
    field_name: str,
) -> datetime:
    raw = _required_string(
        value,
        field_name,
    )

    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(
            raw
        )
    except ValueError as exc:
        raise AclDelegationProductionConfirmationError(
            "Horodatage ACL invalide : "
            + field_name
        ) from exc

    if parsed.tzinfo is None:
        raise AclDelegationProductionConfirmationError(
            "Horodatage ACL sans fuseau : "
            + field_name
        )

    return parsed.astimezone(
        timezone.utc
    )


def _identity_roles(
    identity,
) -> tuple[str, ...]:
    roles = getattr(
        identity,
        "roles",
        (),
    )

    if not isinstance(
        roles,
        (
            list,
            tuple,
            set,
            frozenset,
        ),
    ):
        raise AclDelegationProductionConfirmationError(
            "Roles OIDC ACL invalides"
        )

    normalized = tuple(
        sorted({
            _clean_string(role)
            for role in roles
            if _clean_string(role)
        })
    )

    if not normalized:
        raise AclDelegationProductionConfirmationError(
            "Roles OIDC ACL absents"
        )

    return normalized


def _find_record(
    *,
    registry: dict,
    claim_id: str,
) -> dict:
    normalized = claim_id.casefold()

    matches = [
        record
        for record in registry["records"]
        if _clean_string(
            record.get("claim_id")
        ).casefold()
        == normalized
    ]

    if not matches:
        raise AclDelegationProductionConfirmationError(
            "Claim ACL introuvable"
        )

    if len(matches) != 1:
        raise AclDelegationWriteReplayStorageError(
            "claim_id ACL duplique"
        )

    return matches[0]


def _assert_non_authorizing_record(
    record: dict,
) -> None:
    for key in (
        "job_creation_authorized",
        "runtime_authorized",
        "production_authorized",
        "ad_write_authorized",
    ):
        if record.get(key) is not False:
            raise AclDelegationWriteReplayStorageError(
                "Claim ACL autorisant interdit : "
                + key
            )

    if (
        record.get(
            "prewrite_validation_runtime_authorized"
        )
        is not False
    ):
        raise AclDelegationWriteReplayStorageError(
            "Runtime pre-write encore autorise"
        )


def _assert_same_identity(
    *,
    record: dict,
    identity,
) -> tuple[str, ...]:
    if not isinstance(
        identity,
        AuthenticatedIdentity,
    ):
        raise AclDelegationProductionConfirmationError(
            "Identite OIDC ACL invalide"
        )

    if identity.auth_type != "oidc":
        raise AclDelegationProductionConfirmationError(
            "Authentification OIDC ACL obligatoire"
        )

    claims = identity.claims

    if not isinstance(
        claims,
        dict,
    ):
        raise AclDelegationProductionConfirmationError(
            "Claims OIDC ACL invalides"
        )

    actor_subject = _required_string(
        identity.subject,
        "identity.subject",
    )

    claim_subject = _required_string(
        claims.get("sub"),
        "identity.claims.sub",
    )

    if claim_subject != actor_subject:
        raise AclDelegationProductionConfirmationConflict(
            "Acteur OIDC different : actor_subject"
        )

    actor_issuer = _required_string(
        claims.get("iss"),
        "identity.claims.iss",
    )

    if actor_issuer != OIDC_ISSUER:
        raise AclDelegationProductionConfirmationConflict(
            "Acteur OIDC different : actor_issuer"
        )

    actor_azp = _required_string(
        claims.get("azp"),
        "identity.claims.azp",
    )

    if (
        OIDC_ALLOWED_AZP
        and actor_azp not in OIDC_ALLOWED_AZP
    ):
        raise AclDelegationProductionConfirmationConflict(
            "Acteur OIDC different : actor_azp"
        )

    current = {
        "actor_subject": actor_subject,

        "actor_username": _required_string(
            identity.username,
            "identity.username",
        ),

        "actor_issuer": actor_issuer,
        "actor_azp": actor_azp,
    }

    for key, actual in current.items():
        expected = _required_string(
            record.get(key),
            key,
        )

        if actual != expected:
            raise AclDelegationProductionConfirmationConflict(
                "Acteur OIDC different : "
                + key
            )

    current_roles = _identity_roles(
        identity
    )

    stored_roles = record.get(
        "actor_roles"
    )

    if (
        not isinstance(
            stored_roles,
            list,
        )
        or not stored_roles
    ):
        raise AclDelegationWriteReplayStorageError(
            "Roles claim ACL invalides"
        )

    required_roles = {
        _clean_string(role)
        for role in stored_roles
        if _clean_string(role)
    }

    if not required_roles:
        raise AclDelegationWriteReplayStorageError(
            "Roles claim ACL vides"
        )

    if not required_roles.issubset(
        set(current_roles)
    ):
        raise AclDelegationProductionConfirmationConflict(
            "Roles OIDC modifies depuis le claim"
        )

    return current_roles


def _assert_prewrite_summary(
    record: dict,
) -> None:
    if (
        record.get("state")
        != "prewrite_validated"
    ):
        raise AclDelegationProductionConfirmationConflict(
            "Pre-write ACL non valide"
        )

    if record.get("prewrite_success") is not True:
        raise AclDelegationWriteReplayStorageError(
            "Succes pre-write incoherent"
        )

    summary = record.get(
        "prewrite_result_summary"
    )

    if not isinstance(
        summary,
        dict,
    ):
        raise AclDelegationWriteReplayStorageError(
            "Resume pre-write ACL invalide"
        )

    exact = {
        "prewrite_validated": True,
        "object_guid_revalidated": True,
        "dacl_revalidated": True,
        "principal_sid_revalidated": True,
        "write_performed": False,
        "production_authorized": False,
        "ad_write_authorized": False,
    }

    for key, expected in exact.items():
        if summary.get(key) != expected:
            raise AclDelegationWriteReplayStorageError(
                "Invariant pre-write ACL invalide : "
                + key
            )

    pairs = (
        (
            summary.get(
                "target_object_guid"
            ),
            record.get(
                "target_object_guid"
            ),
        ),
        (
            summary.get(
                "principal_sid"
            ),
            record.get(
                "principal_sid"
            ),
        ),
        (
            summary.get(
                "dacl_sddl_sha256"
            ),
            record.get(
                "dacl_sddl_sha256"
            ),
        ),
        (
            summary.get(
                "acl_fingerprint"
            ),
            record.get(
                "acl_fingerprint"
            ),
        ),
    )

    if any(
        _clean_string(actual).casefold()
        != _clean_string(expected).casefold()
        for actual, expected in pairs
    ):
        raise AclDelegationWriteReplayStorageError(
            "Resume pre-write different du claim"
        )


def _assert_fresh_prewrite(
    *,
    record: dict,
    confirmation_now: datetime,
) -> str:
    completed_raw = _required_string(
        record.get(
            "prewrite_completed_at"
        ),
        "prewrite_completed_at",
    )

    completed_at = _parse_timestamp(
        completed_raw,
        "prewrite_completed_at",
    )

    if (
        completed_at
        > confirmation_now
        + timedelta(
            seconds=(
                ACL_DELEGATION_PRODUCTION_CONFIRMATION_FUTURE_SKEW_SECONDS
            )
        )
    ):
        raise AclDelegationProductionConfirmationError(
            "Pre-write ACL date dans le futur"
        )

    age_seconds = (
        confirmation_now
        - completed_at
    ).total_seconds()

    if (
        age_seconds
        > ACL_DELEGATION_PRODUCTION_CONFIRMATION_MAX_AGE_SECONDS
    ):
        raise AclDelegationProductionConfirmationConflict(
            "Pre-write ACL trop ancien "
            "pour confirmation Production"
        )

    return completed_raw


def _validate_confirmation(
    *,
    record: dict,
    identity,
    claim_id: str,
    ticket_id: str,
    execution_id: str,
    confirm_object_dn: str,
    confirmation_phrase: str,
    now: datetime | None = None,
) -> AclDelegationProductionConfirmation:
    confirmation_now = _normalize_now(
        now
    )

    _assert_non_authorizing_record(
        record
    )

    _assert_prewrite_summary(
        record
    )

    normalized_claim_id = _required_string(
        claim_id,
        "claim_id",
    )

    normalized_ticket_id = _required_string(
        ticket_id,
        "ticket_id",
    )

    normalized_execution_id = _required_string(
        execution_id,
        "execution_id",
    )

    if (
        normalized_claim_id.casefold()
        != _required_string(
            record.get("claim_id"),
            "record.claim_id",
        ).casefold()
    ):
        raise AclDelegationProductionConfirmationConflict(
            "claim_id ACL different"
        )

    if (
        normalized_ticket_id.casefold()
        != _required_string(
            record.get(
                "prewrite_ticket_id"
            ),
            "record.prewrite_ticket_id",
        ).casefold()
    ):
        raise AclDelegationProductionConfirmationConflict(
            "ticket_id ACL different"
        )

    if (
        normalized_execution_id.casefold()
        != _required_string(
            record.get(
                "prewrite_execution_id"
            ),
            "record.prewrite_execution_id",
        ).casefold()
    ):
        raise AclDelegationProductionConfirmationConflict(
            "execution_id ACL different"
        )

    target_dn = _required_string(
        record.get("target_dn"),
        "record.target_dn",
    )

    normalized_confirm_dn = _required_string(
        confirm_object_dn,
        "confirm_object_dn",
    )

    if (
        normalized_confirm_dn.casefold()
        != target_dn.casefold()
    ):
        raise AclDelegationProductionConfirmationConflict(
            "Confirmation DN ACL invalide"
        )

    normalized_phrase = _required_string(
        confirmation_phrase,
        "confirmation_phrase",
    )

    if (
        normalized_phrase
        != ACL_DELEGATION_WRITE_CONFIRMATION_PHRASE
    ):
        raise AclDelegationProductionConfirmationConflict(
            "Phrase de confirmation ACL invalide"
        )

    actor_roles = _assert_same_identity(
        record=record,
        identity=identity,
    )

    completed_at = _assert_fresh_prewrite(
        record=record,
        confirmation_now=confirmation_now,
    )

    return AclDelegationProductionConfirmation(
        contract_version=(
            ACL_DELEGATION_PRODUCTION_CONFIRMATION_CONTRACT_VERSION
        ),
        state="production_confirmation_dormant",

        confirmation_validated=True,

        claim_id=normalized_claim_id,
        ticket_id=normalized_ticket_id,
        execution_id=normalized_execution_id,

        actor_subject=_required_string(
            record.get("actor_subject"),
            "actor_subject",
        ),
        actor_username=_required_string(
            record.get("actor_username"),
            "actor_username",
        ),
        actor_roles=actor_roles,
        actor_issuer=_required_string(
            record.get("actor_issuer"),
            "actor_issuer",
        ),
        actor_azp=_required_string(
            record.get("actor_azp"),
            "actor_azp",
        ),

        target_dn=target_dn,
        target_object_guid=_required_string(
            record.get(
                "target_object_guid"
            ),
            "target_object_guid",
        ),

        principal_dn=_required_string(
            record.get(
                "principal_dn"
            ),
            "principal_dn",
        ),
        principal_sid=_required_string(
            record.get(
                "principal_sid"
            ),
            "principal_sid",
        ),

        access_control_type=_required_string(
            record.get(
                "access_control_type"
            ),
            "access_control_type",
        ),
        rights=tuple(
            record.get("rights")
            or ()
        ),
        inheritance_type=_required_string(
            record.get(
                "inheritance_type"
            ),
            "inheritance_type",
        ),
        object_type_guid=record.get(
            "object_type_guid"
        ),
        inherited_object_type_guid=record.get(
            "inherited_object_type_guid"
        ),

        dacl_sddl_sha256=_required_string(
            record.get(
                "dacl_sddl_sha256"
            ),
            "dacl_sddl_sha256",
        ),
        acl_fingerprint=_required_string(
            record.get(
                "acl_fingerprint"
            ),
            "acl_fingerprint",
        ),

        prewrite_completed_at=completed_at,

        confirm_object_dn=normalized_confirm_dn,
        confirmation_phrase=normalized_phrase,

        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,
    )


def build_acl_delegation_production_confirmation(
    *,
    identity,
    replay_registry_file: Path,
    claim_id: str,
    ticket_id: str,
    execution_id: str,
    confirm_object_dn: str,
    confirmation_phrase: str,
    now: datetime | None = None,
) -> AclDelegationProductionConfirmation:
    normalized_claim_id = _required_string(
        claim_id,
        "claim_id",
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
            registry=registry,
            claim_id=normalized_claim_id,
        )

        return _validate_confirmation(
            record=record,
            identity=identity,
            claim_id=normalized_claim_id,
            ticket_id=ticket_id,
            execution_id=execution_id,
            confirm_object_dn=confirm_object_dn,
            confirmation_phrase=confirmation_phrase,
            now=now,
        )


def assert_acl_delegation_production_confirmation_invariants(
) -> None:
    if not ACL_DELEGATION_PRODUCTION_CONFIRMATION_ENABLED:
        raise RuntimeError(
            "C8.4D-A2B confirmation must remain enabled"
        )

    if ACL_DELEGATION_PRODUCTION_CONFIRMATION_PERSISTENCE_ENABLED:
        raise RuntimeError(
            "C8.4D-A2B persistence must remain disabled"
        )

    if ACL_DELEGATION_PRODUCTION_CONFIRMATION_JOB_CREATION_AUTHORIZED:
        raise RuntimeError(
            "C8.4D-A2B job creation must remain disabled"
        )

    if ACL_DELEGATION_PRODUCTION_CONFIRMATION_RUNTIME_AUTHORIZED:
        raise RuntimeError(
            "C8.4D-A2B runtime must remain disabled"
        )

    if ACL_DELEGATION_PRODUCTION_CONFIRMATION_PRODUCTION_AUTHORIZED:
        raise RuntimeError(
            "C8.4D-A2B Production must remain unauthorized"
        )

    if ACL_DELEGATION_PRODUCTION_CONFIRMATION_AD_WRITE_AUTHORIZED:
        raise RuntimeError(
            "C8.4D-A2B AD writes must remain unauthorized"
        )


assert_acl_delegation_production_confirmation_invariants()
