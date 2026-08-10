from pathlib import Path
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from types import SimpleNamespace

import pytest

from app.core.security import (
    AuthenticatedIdentity,
    OIDC_ALLOWED_AZP,
    OIDC_ISSUER,
)

from app.services.acl_delegation_production_confirmation import (
    ACL_DELEGATION_PRODUCTION_CONFIRMATION_CONTRACT_VERSION,
    AclDelegationProductionConfirmationConflict,
    AclDelegationProductionConfirmationError,
    _validate_confirmation,
)


NOW = datetime(
    2026,
    8,
    10,
    8,
    0,
    0,
    tzinfo=timezone.utc,
)

TARGET_DN = (
    "OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
)

CLAIM_ID = (
    "11111111-1111-4111-8111-111111111111"
)

TICKET_ID = (
    "22222222-2222-4222-8222-222222222222"
)

EXECUTION_ID = (
    "33333333-3333-4333-8333-333333333333"
)

OBJECT_GUID = (
    "8838f739-c817-4b45-90b2-b597ce79312a"
)

PRINCIPAL_SID = (
    "S-1-5-21-1101651174-4260486456-"
    "3261528239-1118"
)

DACL_SHA = (
    "33f513be33e27d30c30b787c1a5aa125"
    "6a7e2058d7d2dbbaef6dfe325cc622fb"
)

ACL_FINGERPRINT = (
    "4624c5730c6ad56e23e4d4fa5480264c"
    "9ee30c7b63b4df232260860ee25a1c80"
)


def allowed_azp() -> str:
    if OIDC_ALLOWED_AZP:
        return sorted(
            OIDC_ALLOWED_AZP
        )[0]

    return "eitas-portal"


def make_identity(
    *,
    subject="subject-eitas-admin",
    username="eitas-admin",
    roles=(
        "UltraAdmin",
    ),
    claim_subject=None,
    issuer=None,
    authorized_party=None,
    auth_type="oidc",
):
    resolved_roles = frozenset(
        roles
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
            allowed_azp()
            if authorized_party is None
            else authorized_party
        ),
        "preferred_username": (
            username
        ),
        "realm_access": {
            "roles": sorted(
                resolved_roles
            ),
        },
    }

    return AuthenticatedIdentity(
        auth_type=auth_type,
        subject=subject,
        username=username,
        roles=resolved_roles,
        claims=claims,
    )

def make_record(**overrides):
    completed = (
        NOW
        - timedelta(
            seconds=5
        )
    ).isoformat()

    record = {
        "state": "prewrite_validated",

        "claim_id": CLAIM_ID,

        "prewrite_ticket_id": (
            TICKET_ID
        ),
        "prewrite_execution_id": (
            EXECUTION_ID
        ),

        "prewrite_completed_at": (
            completed
        ),
        "prewrite_success": True,
        "prewrite_validation_runtime_authorized": (
            False
        ),

        "actor_subject": (
            "subject-eitas-admin"
        ),
        "actor_username": (
            "eitas-admin"
        ),
        "actor_roles": [
            "UltraAdmin",
        ],
        "actor_issuer": OIDC_ISSUER,
        "actor_azp": allowed_azp(),

        "target_dn": TARGET_DN,
        "target_object_guid": (
            OBJECT_GUID
        ),

        "principal_dn": (
            "CN=GG_IT_Admin,"
            "OU=Groups,OU=EITAS,"
            "DC=API,DC=LOCAL"
        ),
        "principal_sid": (
            PRINCIPAL_SID
        ),

        "access_control_type": (
            "Allow"
        ),
        "rights": [
            "ReadProperty",
            "WriteProperty",
        ],
        "inheritance_type": (
            "Descendents"
        ),
        "object_type_guid": None,
        "inherited_object_type_guid": (
            None
        ),

        "dacl_sddl_sha256": (
            DACL_SHA
        ),
        "acl_fingerprint": (
            ACL_FINGERPRINT
        ),

        "job_creation_authorized": (
            False
        ),
        "runtime_authorized": False,
        "production_authorized": (
            False
        ),
        "ad_write_authorized": False,

        "prewrite_result_summary": {
            "contract_version": (
                "c8.4c1"
            ),
            "execution_policy": (
                "prewrite_validation_only"
            ),
            "prewrite_validated": True,
            "object_guid_revalidated": (
                True
            ),
            "dacl_revalidated": True,
            "principal_sid_revalidated": (
                True
            ),
            "target_object_guid": (
                OBJECT_GUID
            ),
            "principal_sid": (
                PRINCIPAL_SID
            ),
            "dacl_sddl_sha256": (
                DACL_SHA
            ),
            "acl_fingerprint": (
                ACL_FINGERPRINT
            ),
            "write_performed": False,
            "production_authorized": (
                False
            ),
            "ad_write_authorized": (
                False
            ),
        },
    }

    record.update(
        overrides
    )

    return record


def validate(
    *,
    record=None,
    identity=None,
    claim_id=CLAIM_ID,
    ticket_id=TICKET_ID,
    execution_id=EXECUTION_ID,
    confirm_object_dn=TARGET_DN,
    confirmation_phrase=(
        "APPLY ACL DELEGATION"
    ),
    now=NOW,
):
    return _validate_confirmation(
        record=(
            record
            if record is not None
            else make_record()
        ),
        identity=(
            identity
            if identity is not None
            else make_identity()
        ),
        claim_id=claim_id,
        ticket_id=ticket_id,
        execution_id=execution_id,
        confirm_object_dn=(
            confirm_object_dn
        ),
        confirmation_phrase=(
            confirmation_phrase
        ),
        now=now,
    )


def test_valid_confirmation_remains_dormant():
    result = validate()

    assert result.contract_version == (
        ACL_DELEGATION_PRODUCTION_CONFIRMATION_CONTRACT_VERSION
    )

    assert result.state == (
        "production_confirmation_dormant"
    )

    assert (
        result.confirmation_validated
        is True
    )

    assert (
        result.job_creation_authorized
        is False
    )

    assert result.runtime_authorized is False
    assert result.production_authorized is False
    assert result.ad_write_authorized is False


def test_confirmation_keeps_exact_binding():
    result = validate()

    assert result.claim_id == CLAIM_ID
    assert result.ticket_id == TICKET_ID
    assert (
        result.execution_id
        == EXECUTION_ID
    )

    assert result.target_dn == TARGET_DN
    assert (
        result.target_object_guid
        == OBJECT_GUID
    )

    assert (
        result.principal_sid
        == PRINCIPAL_SID
    )

    assert (
        result.dacl_sddl_sha256
        == DACL_SHA
    )

    assert (
        result.acl_fingerprint
        == ACL_FINGERPRINT
    )


def test_confirmation_requires_prewrite_validated():
    with pytest.raises(
        AclDelegationProductionConfirmationConflict,
        match="Pre-write ACL non valide",
    ):
        validate(
            record=make_record(
                state="prewrite_failed"
            )
        )


def test_confirmation_rejects_other_ticket():
    with pytest.raises(
        AclDelegationProductionConfirmationConflict,
        match="ticket_id ACL different",
    ):
        validate(
            ticket_id=(
                "aaaaaaaa-aaaa-4aaa-"
                "8aaa-aaaaaaaaaaaa"
            )
        )


def test_confirmation_rejects_other_execution():
    with pytest.raises(
        AclDelegationProductionConfirmationConflict,
        match="execution_id ACL different",
    ):
        validate(
            execution_id=(
                "bbbbbbbb-bbbb-4bbb-"
                "8bbb-bbbbbbbbbbbb"
            )
        )


def test_confirmation_rejects_wrong_dn():
    with pytest.raises(
        AclDelegationProductionConfirmationConflict,
        match="Confirmation DN ACL invalide",
    ):
        validate(
            confirm_object_dn=(
                "OU=Other,"
                "DC=API,DC=LOCAL"
            )
        )


def test_confirmation_rejects_wrong_phrase():
    with pytest.raises(
        AclDelegationProductionConfirmationConflict,
        match="Phrase de confirmation ACL invalide",
    ):
        validate(
            confirmation_phrase=(
                "PRODUCTION"
            )
        )


def test_confirmation_rejects_different_subject():
    with pytest.raises(
        AclDelegationProductionConfirmationConflict,
        match="actor_subject",
    ):
        validate(
            identity=make_identity(
                subject="other-subject"
            )
        )


def test_confirmation_rejects_different_issuer():
    with pytest.raises(
        AclDelegationProductionConfirmationConflict,
        match="actor_issuer",
    ):
        validate(
            identity=make_identity(
                issuer="https://other.invalid"
            )
        )


def test_confirmation_rejects_missing_original_role():
    with pytest.raises(
        AclDelegationProductionConfirmationConflict,
        match="Roles OIDC modifies",
    ):
        validate(
            identity=make_identity(
                roles=(
                    "Viewer",
                )
            )
        )


def test_confirmation_rejects_stale_prewrite():
    record = make_record(
        prewrite_completed_at=(
            NOW
            - timedelta(
                seconds=121
            )
        ).isoformat()
    )

    with pytest.raises(
        AclDelegationProductionConfirmationConflict,
        match="Pre-write ACL trop ancien",
    ):
        validate(
            record=record
        )


def test_confirmation_rejects_far_future_prewrite():
    record = make_record(
        prewrite_completed_at=(
            NOW
            + timedelta(
                seconds=31
            )
        ).isoformat()
    )

    with pytest.raises(
        AclDelegationProductionConfirmationError,
        match="date dans le futur",
    ):
        validate(
            record=record
        )


def test_confirmation_rejects_authorizing_summary():
    record = make_record()

    record[
        "prewrite_result_summary"
    ] = {
        **record[
            "prewrite_result_summary"
        ],
        "ad_write_authorized": True,
    }

    with pytest.raises(
        Exception,
        match="Invariant pre-write ACL invalide",
    ):
        validate(
            record=record
        )


def test_confirmation_rejects_changed_dacl_summary():
    record = make_record()

    record[
        "prewrite_result_summary"
    ] = {
        **record[
            "prewrite_result_summary"
        ],
        "dacl_sddl_sha256": (
            "0" * 64
        ),
    }

    with pytest.raises(
        Exception,
        match="Resume pre-write different",
    ):
        validate(
            record=record
        )


def test_confirmation_never_exposes_write_authorization():
    result = validate()

    assert (
        result.confirmation_validated
        is True
    )

    assert {
        result.job_creation_authorized,
        result.runtime_authorized,
        result.production_authorized,
        result.ad_write_authorized,
    } == {
        False,
    }

# C8.4D-A2C1 persistence tests

from contextlib import contextmanager


@contextmanager
def _a2c1_noop_lock(_path):
    yield


def _a2c1_install_registry(
    monkeypatch,
    record,
):
    import app.services.acl_delegation_production_confirmation_persistence as persistence

    registry = {
        "records": [
            record,
        ],
    }

    writes = []

    monkeypatch.setattr(
        persistence,
        "_normalize_registry_path",
        lambda path: path,
    )

    monkeypatch.setattr(
        persistence,
        "_exclusive_registry_lock",
        _a2c1_noop_lock,
    )

    monkeypatch.setattr(
        persistence,
        "_safe_load_registry",
        lambda _path: registry,
    )

    monkeypatch.setattr(
        persistence,
        "_atomic_write_registry",
        lambda _path, data: writes.append(
            data
        ),
    )

    return (
        persistence,
        registry,
        writes,
    )


def test_a2c1_persists_confirmation_once(
    monkeypatch,
    tmp_path,
):
    record = make_record()

    (
        persistence,
        registry,
        writes,
    ) = _a2c1_install_registry(
        monkeypatch,
        record,
    )

    result = (
        persistence.persist_acl_delegation_production_confirmation(
            identity=make_identity(),
            replay_registry_file=(
                tmp_path / "registry.json"
            ),
            claim_id=CLAIM_ID,
            ticket_id=TICKET_ID,
            execution_id=EXECUTION_ID,
            confirm_object_dn=TARGET_DN,
            confirmation_phrase=(
                "APPLY ACL DELEGATION"
            ),
            now=NOW,
        )
    )

    assert result.state == (
        "production_confirmation_dormant"
    )

    assert result.source_state == (
        "prewrite_validated"
    )

    assert result.confirmation_validated is True
    assert result.confirmation_consumed is True

    assert result.job_creation_authorized is False
    assert result.runtime_authorized is False
    assert result.production_authorized is False
    assert result.ad_write_authorized is False

    stored = registry["records"][0]

    assert stored["state"] == (
        "prewrite_validated"
    )

    assert (
        stored[
            "production_confirmation_validated"
        ]
        is True
    )

    assert (
        stored[
            "production_confirmation_consumed"
        ]
        is True
    )

    assert len(writes) == 1


def test_a2c1_replay_is_rejected(
    monkeypatch,
    tmp_path,
):
    record = make_record(
        production_confirmation_consumed=True,
        production_confirmation_id="existing",
        production_confirmation_digest=(
            "a" * 64
        ),
        production_confirmation_created_at=(
            NOW.isoformat()
        ),
    )

    (
        persistence,
        _registry,
        writes,
    ) = _a2c1_install_registry(
        monkeypatch,
        record,
    )

    with pytest.raises(
        persistence.AclDelegationProductionConfirmationPersistenceConflict,
        match="deja consommee",
    ):
        persistence.persist_acl_delegation_production_confirmation(
            identity=make_identity(),
            replay_registry_file=(
                tmp_path / "registry.json"
            ),
            claim_id=CLAIM_ID,
            ticket_id=TICKET_ID,
            execution_id=EXECUTION_ID,
            confirm_object_dn=TARGET_DN,
            confirmation_phrase=(
                "APPLY ACL DELEGATION"
            ),
            now=NOW,
        )

    assert writes == []


def test_a2c1_wrong_actor_is_not_persisted(
    monkeypatch,
    tmp_path,
):
    record = make_record()

    (
        persistence,
        _registry,
        writes,
    ) = _a2c1_install_registry(
        monkeypatch,
        record,
    )

    with pytest.raises(
        AclDelegationProductionConfirmationConflict,
        match="actor_subject",
    ):
        persistence.persist_acl_delegation_production_confirmation(
            identity=make_identity(
                subject="other-subject"
            ),
            replay_registry_file=(
                tmp_path / "registry.json"
            ),
            claim_id=CLAIM_ID,
            ticket_id=TICKET_ID,
            execution_id=EXECUTION_ID,
            confirm_object_dn=TARGET_DN,
            confirmation_phrase=(
                "APPLY ACL DELEGATION"
            ),
            now=NOW,
        )

    assert writes == []


def test_a2c1_stale_prewrite_is_not_persisted(
    monkeypatch,
    tmp_path,
):
    record = make_record(
        prewrite_completed_at=(
            NOW
            - timedelta(
                seconds=121
            )
        ).isoformat()
    )

    (
        persistence,
        _registry,
        writes,
    ) = _a2c1_install_registry(
        monkeypatch,
        record,
    )

    with pytest.raises(
        AclDelegationProductionConfirmationConflict,
        match="Pre-write ACL trop ancien",
    ):
        persistence.persist_acl_delegation_production_confirmation(
            identity=make_identity(),
            replay_registry_file=(
                tmp_path / "registry.json"
            ),
            claim_id=CLAIM_ID,
            ticket_id=TICKET_ID,
            execution_id=EXECUTION_ID,
            confirm_object_dn=TARGET_DN,
            confirmation_phrase=(
                "APPLY ACL DELEGATION"
            ),
            now=NOW,
        )

    assert writes == []


def test_a2c1_does_not_store_raw_confirmation_phrase(
    monkeypatch,
    tmp_path,
):
    record = make_record()

    (
        persistence,
        registry,
        _writes,
    ) = _a2c1_install_registry(
        monkeypatch,
        record,
    )

    persistence.persist_acl_delegation_production_confirmation(
        identity=make_identity(),
        replay_registry_file=(
            tmp_path / "registry.json"
        ),
        claim_id=CLAIM_ID,
        ticket_id=TICKET_ID,
        execution_id=EXECUTION_ID,
        confirm_object_dn=TARGET_DN,
        confirmation_phrase=(
            "APPLY ACL DELEGATION"
        ),
        now=NOW,
    )

    stored = registry["records"][0]

    assert (
        "production_confirmation_phrase"
        not in stored
    )

    assert len(
        stored[
            "production_confirmation_phrase_sha256"
        ]
    ) == 64


def test_a2c1_persistence_never_authorizes_write(
    monkeypatch,
    tmp_path,
):
    record = make_record()

    (
        persistence,
        registry,
        _writes,
    ) = _a2c1_install_registry(
        monkeypatch,
        record,
    )

    result = (
        persistence.persist_acl_delegation_production_confirmation(
            identity=make_identity(),
            replay_registry_file=(
                tmp_path / "registry.json"
            ),
            claim_id=CLAIM_ID,
            ticket_id=TICKET_ID,
            execution_id=EXECUTION_ID,
            confirm_object_dn=TARGET_DN,
            confirmation_phrase=(
                "APPLY ACL DELEGATION"
            ),
            now=NOW,
        )
    )

    stored = registry["records"][0]

    assert {
        result.job_creation_authorized,
        result.runtime_authorized,
        result.production_authorized,
        result.ad_write_authorized,
        stored[
            "production_confirmation_job_creation_authorized"
        ],
        stored[
            "production_confirmation_runtime_authorized"
        ],
        stored[
            "production_confirmation_production_authorized"
        ],
        stored[
            "production_confirmation_ad_write_authorized"
        ],
    } == {
        False,
    }


def test_c8_4d_a4b2_r2_real_identity_claims():
    confirmation = validate(
        identity=make_identity()
    )

    assert (
        confirmation.actor_subject
        == "subject-eitas-admin"
    )

    assert (
        confirmation.actor_issuer
        == OIDC_ISSUER
    )

    assert (
        confirmation.actor_azp
        == allowed_azp()
    )


def test_c8_4d_a4b2_r2_rejects_claim_subject_mismatch():
    with pytest.raises(
        AclDelegationProductionConfirmationConflict,
        match="actor_subject",
    ):
        validate(
            identity=make_identity(
                claim_subject="different-subject"
            )
        )


def test_c8_4d_a4b2_r2_rejects_different_azp():
    with pytest.raises(
        AclDelegationProductionConfirmationConflict,
        match="actor_azp",
    ):
        validate(
            identity=make_identity(
                authorized_party="other-client"
            )
        )


def test_c8_4d_a4b2_r2_rejects_non_oidc_identity():
    with pytest.raises(
        AclDelegationProductionConfirmationError,
        match="Authentification OIDC ACL obligatoire",
    ):
        validate(
            identity=make_identity(
                auth_type="api_key"
            )
        )


def test_c8_4d_a4b2_r2_source_uses_claims_not_fake_attributes():
    source = Path(
        "api/app/services/"
        "acl_delegation_production_confirmation.py"
    ).read_text(
        encoding="utf-8"
    )

    assert 'claims.get("sub")' in source
    assert 'claims.get("iss")' in source
    assert 'claims.get("azp")' in source

    assert (
        'identity.auth_type != "oidc"'
        in source
    )

    assert (
        'getattr(\n'
        '                identity,\n'
        '                "issuer"'
        not in source
    )

    assert (
        'getattr(\n'
        '                identity,\n'
        '                "azp"'
        not in source
    )
