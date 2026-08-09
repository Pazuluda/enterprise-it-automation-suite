from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.security import (
    AuthenticatedIdentity,
    OIDC_ALLOWED_AZP,
    OIDC_AUDIENCE,
    OIDC_ISSUER,
    OIDC_LEEWAY_SECONDS,
)
from app.services.acl_delegation_write_trust import (
    AclDelegationWriteTrustBadRequest,
    resolve_trusted_acl_delegation_write_evidence,
)


ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_CONTRACT_VERSION = (
    "c8.4b3"
)

ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_ENABLED = True

ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_TTL_SECONDS = 60

ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_JOB_CREATION_ENABLED = False
ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_RUNTIME_ENABLED = False
ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_PRODUCTION_ENABLED = False
ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_AD_WRITE_ENABLED = False


REQUIRED_WRITE_ROLES = frozenset({
    "ADAdmin",
    "UltraAdmin",
})


FORBIDDEN_CLIENT_IDENTITY_KEYS = frozenset({
    "actor",
    "actor_subject",
    "actor_username",
    "actor_roles",
    "auth_type",
    "claims",
    "created_by",
    "evidence_digest",
    "consumption_id",
    "server_nonce",
    "issued_at",
    "expires_at",
})


class AclDelegationWriteIdentityEnvelopeError(
    ValueError
):
    pass


@dataclass(frozen=True)
class AclDelegationWriteIdentityEnvelope:
    contract_version: str
    execution_policy: str

    server_nonce: str
    issued_at: str
    expires_at: str

    actor_auth_type: str
    actor_subject: str
    actor_username: str
    actor_roles: tuple[str, ...]

    actor_issuer: str
    actor_azp: str
    actor_audience: tuple[str, ...]
    actor_jti: str | None
    actor_token_iat: float
    actor_token_exp: float

    simulation_job_id: str
    security_descriptor_job_id: str
    evidence_digest: str
    trusted_source: str

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

    envelope_digest: str

    trusted_evidence_loaded: bool
    binding_validated: bool

    replay_consumed: bool
    replay_consumption_id: str | None
    replay_consumption_required: bool

    job_creation_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    ad_write_authorized: bool


def _clean_string(value: Any) -> str:
    return str(value or "").strip()


def _normalize_now(
    now: datetime | None,
) -> datetime:
    resolved = (
        now
        if now is not None
        else datetime.now(timezone.utc)
    )

    if not isinstance(resolved, datetime):
        raise AclDelegationWriteIdentityEnvelopeError(
            "Horodatage B3 invalide"
        )

    if resolved.tzinfo is None:
        raise AclDelegationWriteIdentityEnvelopeError(
            "Horodatage B3 sans fuseau"
        )

    return resolved.astimezone(
        timezone.utc
    )


def _numeric_date(
    value: Any,
    field_name: str,
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise AclDelegationWriteIdentityEnvelopeError(
            f"Claim {field_name} invalide"
        )

    return float(value)


def _normalize_audience(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return tuple()

    if isinstance(value, str):
        cleaned = value.strip()

        if not cleaned:
            raise AclDelegationWriteIdentityEnvelopeError(
                "Claim aud vide"
            )

        return (cleaned,)

    if not isinstance(value, list):
        raise AclDelegationWriteIdentityEnvelopeError(
            "Claim aud invalide"
        )

    normalized = []

    for item in value:
        if not isinstance(item, str):
            raise AclDelegationWriteIdentityEnvelopeError(
                "Valeur aud invalide"
            )

        cleaned = item.strip()

        if not cleaned:
            raise AclDelegationWriteIdentityEnvelopeError(
                "Valeur aud vide"
            )

        if cleaned not in normalized:
            normalized.append(cleaned)

    return tuple(
        sorted(
            normalized,
            key=str.casefold,
        )
    )


def _claim_roles(
    claims: dict[str, Any],
) -> frozenset[str]:
    realm_access = claims.get(
        "realm_access"
    )

    if not isinstance(
        realm_access,
        dict,
    ):
        return frozenset()

    roles = realm_access.get("roles")

    if not isinstance(roles, list):
        return frozenset()

    return frozenset(
        role
        for role in roles
        if (
            isinstance(role, str)
            and role
        )
    )


def _validate_authenticated_actor(
    identity: AuthenticatedIdentity,
    now: datetime,
) -> dict[str, Any]:
    if not isinstance(
        identity,
        AuthenticatedIdentity,
    ):
        raise AclDelegationWriteIdentityEnvelopeError(
            "Identite authentifiee B3 requise"
        )

    if identity.auth_type != "oidc":
        raise AclDelegationWriteIdentityEnvelopeError(
            "B3 exige une identite OIDC"
        )

    subject = _clean_string(
        identity.subject
    )

    username = _clean_string(
        identity.username
    )

    if not subject:
        raise AclDelegationWriteIdentityEnvelopeError(
            "Sujet OIDC B3 manquant"
        )

    if not username:
        raise AclDelegationWriteIdentityEnvelopeError(
            "Nom utilisateur OIDC B3 manquant"
        )

    claims = identity.claims

    if not isinstance(claims, dict):
        raise AclDelegationWriteIdentityEnvelopeError(
            "Claims OIDC B3 invalides"
        )

    claim_subject = _clean_string(
        claims.get("sub")
    )

    if claim_subject != subject:
        raise AclDelegationWriteIdentityEnvelopeError(
            "Sujet OIDC incoherent"
        )

    issuer = _clean_string(
        claims.get("iss")
    )

    if issuer != OIDC_ISSUER:
        raise AclDelegationWriteIdentityEnvelopeError(
            "Issuer OIDC B3 invalide"
        )

    azp = _clean_string(
        claims.get("azp")
    )

    if not azp:
        raise AclDelegationWriteIdentityEnvelopeError(
            "azp OIDC B3 manquant"
        )

    if (
        OIDC_ALLOWED_AZP
        and azp not in OIDC_ALLOWED_AZP
    ):
        raise AclDelegationWriteIdentityEnvelopeError(
            "azp OIDC B3 non autorise"
        )

    claim_roles = _claim_roles(
        claims
    )

    if claim_roles != identity.roles:
        raise AclDelegationWriteIdentityEnvelopeError(
            "Roles OIDC B3 incoherents"
        )

    if identity.roles.isdisjoint(
        REQUIRED_WRITE_ROLES
    ):
        raise AclDelegationWriteIdentityEnvelopeError(
            "Role ACL B3 insuffisant"
        )

    expected_username = (
        claims.get("preferred_username")
        or claims.get("email")
        or subject
    )

    if not isinstance(
        expected_username,
        str,
    ):
        expected_username = subject

    expected_username = (
        expected_username.strip()
        or subject
    )

    if username != expected_username:
        raise AclDelegationWriteIdentityEnvelopeError(
            "Nom utilisateur OIDC incoherent"
        )

    token_iat = _numeric_date(
        claims.get("iat"),
        "iat",
    )

    token_exp = _numeric_date(
        claims.get("exp"),
        "exp",
    )

    now_timestamp = now.timestamp()

    if (
        token_iat
        > (
            now_timestamp
            + OIDC_LEEWAY_SECONDS
        )
    ):
        raise AclDelegationWriteIdentityEnvelopeError(
            "Token OIDC date dans le futur"
        )

    if token_exp <= now_timestamp:
        raise AclDelegationWriteIdentityEnvelopeError(
            "Token OIDC expire pour B3"
        )

    audience = _normalize_audience(
        claims.get("aud")
    )

    if (
        OIDC_AUDIENCE is not None
        and OIDC_AUDIENCE not in audience
    ):
        raise AclDelegationWriteIdentityEnvelopeError(
            "Audience OIDC B3 invalide"
        )

    raw_jti = claims.get("jti")

    if raw_jti is None:
        jti = None
    else:
        if not isinstance(raw_jti, str):
            raise AclDelegationWriteIdentityEnvelopeError(
                "Claim jti invalide"
            )

        jti = raw_jti.strip()

        if not jti:
            raise AclDelegationWriteIdentityEnvelopeError(
                "Claim jti vide"
            )

    return {
        "subject": subject,
        "username": username,
        "roles": tuple(
            sorted(identity.roles)
        ),
        "issuer": issuer,
        "azp": azp,
        "audience": audience,
        "jti": jti,
        "token_iat": token_iat,
        "token_exp": token_exp,
    }


def _build_envelope_digest(
    material: dict[str, Any],
) -> str:
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def build_acl_delegation_write_identity_envelope(
    *,
    identity: AuthenticatedIdentity,
    ad_admin_jobs_file: Path,
    ad_explorer_jobs_file: Path,
    intent_payload: dict,
    now: datetime | None = None,
) -> AclDelegationWriteIdentityEnvelope:
    if not (
        ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_ENABLED
    ):
        raise AclDelegationWriteIdentityEnvelopeError(
            "Enveloppe ACL B3 desactivee"
        )

    if not isinstance(intent_payload, dict):
        raise AclDelegationWriteIdentityEnvelopeError(
            "Intention ACL B3 invalide"
        )

    injected_identity_keys = sorted(
        set(intent_payload)
        & FORBIDDEN_CLIENT_IDENTITY_KEYS
    )

    if injected_identity_keys:
        raise AclDelegationWriteIdentityEnvelopeError(
            "Champs d'identite client interdits : "
            + ", ".join(injected_identity_keys)
        )

    validation_now = _normalize_now(
        now
    )

    actor = _validate_authenticated_actor(
        identity,
        validation_now,
    )

    try:
        evidence = (
            resolve_trusted_acl_delegation_write_evidence(
                ad_admin_jobs_file=(
                    ad_admin_jobs_file
                ),
                ad_explorer_jobs_file=(
                    ad_explorer_jobs_file
                ),
                intent_payload=intent_payload,
                now=validation_now,
            )
        )
    except AclDelegationWriteTrustBadRequest as exc:
        raise AclDelegationWriteIdentityEnvelopeError(
            str(exc)
        ) from exc

    if (
        evidence.trusted_evidence_loaded
        is not True
    ):
        raise AclDelegationWriteIdentityEnvelopeError(
            "Preuve serveur B3 non chargee"
        )

    if evidence.binding_validated is not True:
        raise AclDelegationWriteIdentityEnvelopeError(
            "Binding serveur B3 non valide"
        )

    if any((
        evidence.job_creation_authorized,
        evidence.runtime_authorized,
        evidence.production_authorized,
        evidence.ad_write_authorized,
    )):
        raise AclDelegationWriteIdentityEnvelopeError(
            "Preuve B3 autorisante interdite"
        )

    issued_at = validation_now

    token_expiry = datetime.fromtimestamp(
        actor["token_exp"],
        tz=timezone.utc,
    )

    server_expiry = (
        validation_now
        + timedelta(
            seconds=(
                ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_TTL_SECONDS
            )
        )
    )

    expires_at = min(
        token_expiry,
        server_expiry,
    )

    if expires_at <= issued_at:
        raise AclDelegationWriteIdentityEnvelopeError(
            "Expiration B3 invalide"
        )

    server_nonce = secrets.token_hex(
        32
    )

    intent = evidence.intent
    binding = evidence.binding

    material = {
        "contract_version": (
            ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_CONTRACT_VERSION
        ),
        "execution_policy": (
            "identity_bound_dormant"
        ),
        "server_nonce": server_nonce,
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "actor": {
            "auth_type": "oidc",
            "subject": actor["subject"],
            "username": actor["username"],
            "roles": list(
                actor["roles"]
            ),
            "issuer": actor["issuer"],
            "azp": actor["azp"],
            "audience": list(
                actor["audience"]
            ),
            "jti": actor["jti"],
            "token_iat": actor["token_iat"],
            "token_exp": actor["token_exp"],
        },
        "evidence": {
            "simulation_job_id": (
                evidence.simulation_job_id
            ),
            "security_descriptor_job_id": (
                evidence.security_descriptor_job_id
            ),
            "evidence_digest": (
                evidence.evidence_digest
            ),
            "trusted_source": (
                evidence.trusted_source
            ),
        },
        "target": {
            "dn": binding.target_dn,
            "object_guid": (
                binding.target_object_guid
            ),
        },
        "principal": {
            "dn": binding.principal_dn,
            "sid": binding.principal_sid,
        },
        "ace": {
            "access_control_type": (
                intent.access_control_type
            ),
            "rights": sorted(
                intent.rights,
                key=str.casefold,
            ),
            "inheritance_type": (
                intent.inheritance_type
            ),
            "object_type_guid": (
                intent.object_type_guid
            ),
            "inherited_object_type_guid": (
                intent.inherited_object_type_guid
            ),
        },
        "dacl": {
            "dacl_sddl_sha256": (
                binding.dacl_sddl_sha256
            ),
            "acl_fingerprint": (
                binding.acl_fingerprint
            ),
        },
        "anti_replay": {
            "consumed": False,
            "consumption_id": None,
            "consumption_required": True,
        },
        "authorization": {
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    }

    envelope_digest = (
        _build_envelope_digest(
            material
        )
    )

    return AclDelegationWriteIdentityEnvelope(
        contract_version=(
            ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_CONTRACT_VERSION
        ),
        execution_policy=(
            "identity_bound_dormant"
        ),
        server_nonce=server_nonce,
        issued_at=issued_at.isoformat(),
        expires_at=expires_at.isoformat(),
        actor_auth_type="oidc",
        actor_subject=actor["subject"],
        actor_username=actor["username"],
        actor_roles=actor["roles"],
        actor_issuer=actor["issuer"],
        actor_azp=actor["azp"],
        actor_audience=actor["audience"],
        actor_jti=actor["jti"],
        actor_token_iat=actor["token_iat"],
        actor_token_exp=actor["token_exp"],
        simulation_job_id=(
            evidence.simulation_job_id
        ),
        security_descriptor_job_id=(
            evidence.security_descriptor_job_id
        ),
        evidence_digest=(
            evidence.evidence_digest
        ),
        trusted_source=(
            evidence.trusted_source
        ),
        target_dn=binding.target_dn,
        target_object_guid=(
            binding.target_object_guid
        ),
        principal_dn=(
            binding.principal_dn
        ),
        principal_sid=(
            binding.principal_sid
        ),
        access_control_type=(
            intent.access_control_type
        ),
        rights=tuple(
            sorted(
                intent.rights,
                key=str.casefold,
            )
        ),
        inheritance_type=(
            intent.inheritance_type
        ),
        object_type_guid=(
            intent.object_type_guid
        ),
        inherited_object_type_guid=(
            intent.inherited_object_type_guid
        ),
        dacl_sddl_sha256=(
            binding.dacl_sddl_sha256
        ),
        acl_fingerprint=(
            binding.acl_fingerprint
        ),
        envelope_digest=envelope_digest,
        trusted_evidence_loaded=True,
        binding_validated=True,
        replay_consumed=False,
        replay_consumption_id=None,
        replay_consumption_required=True,
        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,
    )


def assert_acl_delegation_write_identity_envelope_invariants(
) -> None:
    if not (
        ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_ENABLED
    ):
        raise RuntimeError(
            "C8.4B3 identity envelope must remain enabled"
        )

    if (
        ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_JOB_CREATION_ENABLED
    ):
        raise RuntimeError(
            "C8.4B3 job creation must remain disabled"
        )

    if (
        ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_RUNTIME_ENABLED
    ):
        raise RuntimeError(
            "C8.4B3 runtime must remain disabled"
        )

    if (
        ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_PRODUCTION_ENABLED
    ):
        raise RuntimeError(
            "C8.4B3 Production must remain disabled"
        )

    if (
        ACL_DELEGATION_WRITE_IDENTITY_ENVELOPE_AD_WRITE_ENABLED
    ):
        raise RuntimeError(
            "C8.4B3 AD writes must remain disabled"
        )


assert_acl_delegation_write_identity_envelope_invariants()
