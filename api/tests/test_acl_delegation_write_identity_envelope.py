from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.security import (
    AuthenticatedIdentity,
    OIDC_ALLOWED_AZP,
    OIDC_AUDIENCE,
    OIDC_ISSUER,
)
import app.services.acl_delegation_write_identity_envelope as envelope_module
from app.services.acl_delegation_write_identity_envelope import (
    AclDelegationWriteIdentityEnvelopeError,
    build_acl_delegation_write_identity_envelope,
)


NOW = datetime(
    2026,
    8,
    9,
    16,
    0,
    0,
    tzinfo=timezone.utc,
)

TARGET_DN = (
    "OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
)

TARGET_GUID = (
    "8838f739-c817-4b45-"
    "90b2-b597ce79312a"
)

PRINCIPAL_DN = (
    "CN=GG_IT_Admin,"
    "OU=Groups,OU=EITAS,"
    "DC=API,DC=LOCAL"
)

PRINCIPAL_SID = (
    "S-1-5-21-1101651174-"
    "4260486456-3261528239-1118"
)

DACL_SHA = "3" * 64
ACL_FINGERPRINT = "4" * 64
EVIDENCE_DIGEST = "5" * 64


def azp() -> str:
    if OIDC_ALLOWED_AZP:
        return sorted(
            OIDC_ALLOWED_AZP
        )[0]

    return "eitas-portal"


def identity(
    *,
    subject="oidc-user-123",
    username="eitas-admin",
    roles=None,
    claim_subject=None,
    issuer=None,
    authorized_party=None,
    jti=None,
):
    resolved_roles = (
        frozenset({
            "ADAdmin",
            "Viewer",
        })
        if roles is None
        else frozenset(roles)
    )

    claims = {
        "sub": (
            subject
            if claim_subject is None
            else claim_subject
        ),
        "iss": (
            OIDC_ISSUER
            if issuer is None
            else issuer
        ),
        "azp": (
            azp()
            if authorized_party is None
            else authorized_party
        ),
        "iat": NOW.timestamp() - 30,
        "exp": NOW.timestamp() + 300,
        "preferred_username": username,
        "realm_access": {
            "roles": sorted(
                resolved_roles
            ),
        },
    }

    if OIDC_AUDIENCE is not None:
        claims["aud"] = OIDC_AUDIENCE

    if jti is not None:
        claims["jti"] = jti

    return AuthenticatedIdentity(
        auth_type="oidc",
        subject=subject,
        username=username,
        roles=resolved_roles,
        claims=claims,
    )


def intent():
    return {
        "action": "apply_acl_delegation",
        "mode": "Production",
        "object_dn": TARGET_DN,
        "principal_identity": "GG_IT_Admin",
        "access_control_type": "Allow",
        "rights": [
            "ReadProperty",
            "WriteProperty",
        ],
        "inheritance_type": "Descendents",
        "object_type_guid": None,
        "inherited_object_type_guid": None,
        "simulation_job_id": (
            "11111111-1111-4111-"
            "8111-111111111111"
        ),
        "security_descriptor_job_id": (
            "22222222-2222-4222-"
            "8222-222222222222"
        ),
        "expected_acl_fingerprint": (
            ACL_FINGERPRINT
        ),
        "confirm_object_dn": TARGET_DN,
        "confirmation_phrase": (
            "APPLY ACL DELEGATION"
        ),
    }


def evidence():
    write_intent = SimpleNamespace(
        access_control_type="Allow",
        rights=(
            "ReadProperty",
            "WriteProperty",
        ),
        inheritance_type="Descendents",
        object_type_guid=None,
        inherited_object_type_guid=None,
    )

    binding = SimpleNamespace(
        target_dn=TARGET_DN,
        target_object_guid=TARGET_GUID,
        principal_dn=PRINCIPAL_DN,
        principal_sid=PRINCIPAL_SID,
        dacl_sddl_sha256=DACL_SHA,
        acl_fingerprint=ACL_FINGERPRINT,
    )

    return SimpleNamespace(
        intent=write_intent,
        binding=binding,
        simulation_job_id=(
            "11111111-1111-4111-"
            "8111-111111111111"
        ),
        security_descriptor_job_id=(
            "22222222-2222-4222-"
            "8222-222222222222"
        ),
        target_object_guid=TARGET_GUID,
        evidence_digest=EVIDENCE_DIGEST,
        trusted_source="server_job_storage",
        trusted_evidence_loaded=True,
        binding_validated=True,
        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,
    )


@pytest.fixture
def trusted_resolver(monkeypatch):
    value = evidence()

    def fake_resolver(**kwargs):
        assert kwargs[
            "ad_admin_jobs_file"
        ] == Path("/tmp/admin.json")

        assert kwargs[
            "ad_explorer_jobs_file"
        ] == Path("/tmp/explorer.json")

        assert kwargs[
            "intent_payload"
        ]["action"] == (
            "apply_acl_delegation"
        )

        return value

    monkeypatch.setattr(
        envelope_module,
        "resolve_trusted_acl_delegation_write_evidence",
        fake_resolver,
    )

    monkeypatch.setattr(
        envelope_module.secrets,
        "token_hex",
        lambda size: "a" * 64,
    )

    return value


def build(actor):
    return (
        build_acl_delegation_write_identity_envelope(
            identity=actor,
            ad_admin_jobs_file=Path(
                "/tmp/admin.json"
            ),
            ad_explorer_jobs_file=Path(
                "/tmp/explorer.json"
            ),
            intent_payload=intent(),
            now=NOW,
        )
    )


def test_c8_4b3_binds_oidc_actor_and_evidence(
    trusted_resolver,
):
    result = build(
        identity(
            jti="token-jti-123",
        )
    )

    assert result.contract_version == "c8.4b3"
    assert result.actor_auth_type == "oidc"
    assert result.actor_subject == "oidc-user-123"
    assert result.actor_username == "eitas-admin"
    assert "ADAdmin" in result.actor_roles

    assert result.actor_issuer == OIDC_ISSUER
    assert result.actor_azp == azp()
    assert result.actor_jti == "token-jti-123"

    assert result.target_dn == TARGET_DN
    assert result.target_object_guid == TARGET_GUID
    assert result.principal_sid == PRINCIPAL_SID

    assert result.evidence_digest == EVIDENCE_DIGEST
    assert result.dacl_sddl_sha256 == DACL_SHA
    assert result.acl_fingerprint == ACL_FINGERPRINT

    assert len(result.server_nonce) == 64
    assert len(result.envelope_digest) == 64


def test_c8_4b3_jti_is_optional(
    trusted_resolver,
):
    result = build(
        identity()
    )

    assert result.actor_jti is None


def test_c8_4b3_remains_strictly_non_authorizing(
    trusted_resolver,
):
    result = build(
        identity()
    )

    assert result.trusted_evidence_loaded is True
    assert result.binding_validated is True

    assert result.replay_consumed is False
    assert result.replay_consumption_id is None
    assert result.replay_consumption_required is True

    assert result.job_creation_authorized is False
    assert result.runtime_authorized is False
    assert result.production_authorized is False
    assert result.ad_write_authorized is False


def test_c8_4b3_rejects_api_key_identity(
    trusted_resolver,
):
    actor = AuthenticatedIdentity(
        auth_type="api_key",
        subject="worker-api-key",
        username="worker-api-key",
        roles=frozenset(),
        claims={},
    )

    with pytest.raises(
        AclDelegationWriteIdentityEnvelopeError,
        match="OIDC",
    ):
        build(actor)


def test_c8_4b3_rejects_insufficient_role(
    trusted_resolver,
):
    with pytest.raises(
        AclDelegationWriteIdentityEnvelopeError,
        match="Role ACL B3 insuffisant",
    ):
        build(
            identity(
                roles={"Viewer"},
            )
        )


def test_c8_4b3_rejects_subject_mismatch(
    trusted_resolver,
):
    with pytest.raises(
        AclDelegationWriteIdentityEnvelopeError,
        match="Sujet OIDC incoherent",
    ):
        build(
            identity(
                claim_subject="other-subject",
            )
        )


def test_c8_4b3_rejects_issuer_mismatch(
    trusted_resolver,
):
    with pytest.raises(
        AclDelegationWriteIdentityEnvelopeError,
        match="Issuer",
    ):
        build(
            identity(
                issuer=(
                    "https://invalid.example/"
                    "realms/eitas"
                ),
            )
        )


def test_c8_4b3_rejects_azp_mismatch(
    trusted_resolver,
):
    if not OIDC_ALLOWED_AZP:
        pytest.skip(
            "No configured AZP allowlist"
        )

    with pytest.raises(
        AclDelegationWriteIdentityEnvelopeError,
        match="azp",
    ):
        build(
            identity(
                authorized_party=(
                    "untrusted-client"
                ),
            )
        )


@pytest.mark.parametrize(
    "field",
    [
        "created_by",
        "actor_subject",
        "actor_roles",
        "claims",
        "consumption_id",
        "server_nonce",
    ],
)
def test_c8_4b3_rejects_client_identity_injection(
    trusted_resolver,
    field,
):
    payload = intent()
    payload[field] = "attacker-controlled"

    with pytest.raises(
        AclDelegationWriteIdentityEnvelopeError,
        match="interdits",
    ):
        build_acl_delegation_write_identity_envelope(
            identity=identity(),
            ad_admin_jobs_file=Path(
                "/tmp/admin.json"
            ),
            ad_explorer_jobs_file=Path(
                "/tmp/explorer.json"
            ),
            intent_payload=payload,
            now=NOW,
        )


def test_c8_4b3_digest_changes_with_server_nonce(
    trusted_resolver,
    monkeypatch,
):
    values = iter([
        "a" * 64,
        "b" * 64,
    ])

    monkeypatch.setattr(
        envelope_module.secrets,
        "token_hex",
        lambda size: next(values),
    )

    first = build(identity())
    second = build(identity())

    assert first.server_nonce != second.server_nonce
    assert first.envelope_digest != second.envelope_digest


def test_c8_4b3_does_not_consume_replay_boundary():
    source = Path(
        "api/app/services/"
        "acl_delegation_write_identity_envelope.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "acl_delegation_write_replay"
        not in source
    )

    assert (
        "replay_consumed=False"
        in source
    )


def test_c8_4b3_does_not_open_apply_runtime():
    admin_source = Path(
        "api/app/services/ad_admin.py"
    ).read_text(
        encoding="utf-8"
    )

    main_source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    worker_source = Path(
        "agent-windows/modules/"
        "EitasAdAdmin.ps1"
    ).read_text(
        encoding="utf-8"
    )

    assert "apply_acl_delegation" not in admin_source
    assert "apply_acl_delegation" not in main_source
    assert "apply_acl_delegation" not in worker_source


def test_c8_4b3_has_no_acl_write_primitive():
    source = Path(
        "api/app/services/"
        "acl_delegation_write_identity_envelope.py"
    ).read_text(
        encoding="utf-8"
    )

    for primitive in (
        "Set-Acl",
        "SetAccessRule",
        "AddAccessRule",
        "RemoveAccessRule",
        "ResetAccessRule",
        "SetOwner",
        "ActiveDirectoryAccessRule",
    ):
        assert primitive not in source
