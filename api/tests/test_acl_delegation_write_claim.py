from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.security import AuthenticatedIdentity
import app.services.acl_delegation_write_claim as claim_module
from app.services.acl_delegation_write_claim import (
    AclDelegationWriteClaimConflict,
    claim_acl_delegation_write_intent,
)


NOW = datetime(
    2026,
    8,
    9,
    17,
    30,
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


def fake_identity():
    return AuthenticatedIdentity(
        auth_type="oidc",
        subject="subject-123",
        username="eitas-admin",
        roles=frozenset({
            "UltraAdmin",
        }),
        claims={},
    )


def fake_envelope():
    return SimpleNamespace(
        trusted_evidence_loaded=True,
        binding_validated=True,

        replay_consumed=False,
        replay_consumption_id=None,
        replay_consumption_required=True,

        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,

        envelope_digest="1" * 64,
        evidence_digest="2" * 64,

        simulation_job_id=(
            "11111111-1111-4111-"
            "8111-111111111111"
        ),
        security_descriptor_job_id=(
            "22222222-2222-4222-"
            "8222-222222222222"
        ),

        target_dn=TARGET_DN,
        target_object_guid=TARGET_GUID,

        principal_dn=PRINCIPAL_DN,
        principal_sid=PRINCIPAL_SID,

        access_control_type="Allow",
        rights=(
            "ReadProperty",
            "WriteProperty",
        ),
        inheritance_type="Descendents",
        object_type_guid=None,
        inherited_object_type_guid=None,

        dacl_sddl_sha256="3" * 64,
        acl_fingerprint="4" * 64,

        actor_subject="subject-123",
        actor_username="eitas-admin",
        actor_roles=(
            "UltraAdmin",
        ),
        actor_issuer=(
            "https://issuer.example/"
            "realms/eitas"
        ),
        actor_azp="eitas-portal",
        actor_jti=None,

        server_nonce="5" * 64,
        issued_at=NOW.isoformat(),
        expires_at=(
            "2026-08-09T17:31:00+00:00"
        ),
    )


@pytest.fixture
def envelope_builder(monkeypatch):
    value = fake_envelope()

    monkeypatch.setattr(
        claim_module,
        "build_acl_delegation_write_identity_envelope",
        lambda **kwargs: value,
    )

    return value


def claim(tmp_path):
    return claim_acl_delegation_write_intent(
        identity=fake_identity(),
        ad_admin_jobs_file=(
            tmp_path / "admin.json"
        ),
        ad_explorer_jobs_file=(
            tmp_path / "explorer.json"
        ),
        replay_registry_file=(
            tmp_path / "replay.json"
        ),
        intent_payload={
            "action": "apply_acl_delegation",
        },
        now=NOW,
    )


def test_c8_4b4_creates_atomic_dormant_claim(
    tmp_path,
    envelope_builder,
):
    result = claim(tmp_path)

    assert result.state == "claimed_dormant"
    assert result.replay_consumed is True

    assert result.target_object_guid == TARGET_GUID
    assert result.principal_sid == PRINCIPAL_SID

    assert result.actor_subject == "subject-123"
    assert result.actor_roles == (
        "UltraAdmin",
    )

    assert result.job_creation_authorized is False
    assert result.runtime_authorized is False
    assert result.production_authorized is False
    assert result.ad_write_authorized is False


def test_c8_4b4_registry_contains_one_combined_record(
    tmp_path,
    envelope_builder,
):
    import json

    result = claim(tmp_path)

    registry = json.loads(
        (
            tmp_path / "replay.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert len(registry["records"]) == 1

    record = registry["records"][0]

    assert record["state"] == "claimed_dormant"

    assert (
        record["claim_id"]
        == result.claim_id
    )

    assert (
        record["consumption_id"]
        == result.consumption_id
    )

    assert (
        record["envelope_digest"]
        == result.envelope_digest
    )

    assert record[
        "job_creation_authorized"
    ] is False

    assert record[
        "runtime_authorized"
    ] is False

    assert record[
        "production_authorized"
    ] is False

    assert record[
        "ad_write_authorized"
    ] is False


def test_c8_4b4_exact_replay_is_rejected(
    tmp_path,
    envelope_builder,
):
    claim(tmp_path)

    with pytest.raises(
        AclDelegationWriteClaimConflict,
        match="deja consommee",
    ):
        claim(tmp_path)


def test_c8_4b4_registry_is_private(
    tmp_path,
    envelope_builder,
):
    claim(tmp_path)

    mode = (
        tmp_path / "replay.json"
    ).stat().st_mode & 0o777

    assert mode == 0o600


def test_c8_4b4_rejects_authorizing_envelope(
    tmp_path,
    envelope_builder,
    monkeypatch,
):
    unsafe = fake_envelope()
    unsafe.production_authorized = True

    monkeypatch.setattr(
        claim_module,
        "build_acl_delegation_write_identity_envelope",
        lambda **kwargs: unsafe,
    )

    with pytest.raises(
        ValueError,
        match="autorisante",
    ):
        claim(tmp_path)


def test_c8_4b4_no_generic_runtime_exposure():
    admin = Path(
        "api/app/services/ad_admin.py"
    ).read_text(
        encoding="utf-8"
    )

    worker = Path(
        "agent-windows/modules/"
        "EitasAdAdmin.ps1"
    ).read_text(
        encoding="utf-8"
    )

    frontend = Path(
        "frontend/src/App.jsx"
    ).read_text(
        encoding="utf-8"
    )

    assert "apply_acl_delegation" not in admin
    assert "apply_acl_delegation" not in worker
    assert "apply_acl_delegation" not in frontend


def test_c8_4b4_no_acl_write_primitive():
    source = Path(
        "api/app/services/"
        "acl_delegation_write_claim.py"
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


# ============================================================
# C8.4B4 hardening gates
# ============================================================

import json
import multiprocessing

from app.services.acl_delegation_write_replay import (
    AclDelegationWriteReplayStorageError,
)


def _c8_4b4_concurrent_worker(
    root,
    queue,
):
    claim_module.build_acl_delegation_write_identity_envelope = (
        lambda **kwargs: fake_envelope()
    )

    try:
        result = (
            claim_acl_delegation_write_intent(
                identity=fake_identity(),
                ad_admin_jobs_file=(
                    Path(root) / "admin.json"
                ),
                ad_explorer_jobs_file=(
                    Path(root) / "explorer.json"
                ),
                replay_registry_file=(
                    Path(root) / "replay.json"
                ),
                intent_payload={
                    "action": (
                        "apply_acl_delegation"
                    ),
                },
                now=NOW,
            )
        )

        queue.put(
            (
                "winner",
                result.claim_id,
            )
        )

    except AclDelegationWriteClaimConflict:
        queue.put(
            (
                "conflict",
                "",
            )
        )

    except Exception as exc:
        queue.put(
            (
                "error",
                repr(exc),
            )
        )


def test_c8_4b4_interprocess_race_has_one_winner(
    tmp_path,
):
    ctx = multiprocessing.get_context(
        "fork"
    )

    queue = ctx.Queue()

    processes = [
        ctx.Process(
            target=(
                _c8_4b4_concurrent_worker
            ),
            args=(
                str(tmp_path),
                queue,
            ),
        )
        for _ in range(4)
    ]

    for process in processes:
        process.start()

    for process in processes:
        process.join(10)

    for process in processes:
        assert not process.is_alive()
        assert process.exitcode == 0

    results = [
        queue.get(timeout=2)
        for _ in processes
    ]

    winners = [
        item
        for item in results
        if item[0] == "winner"
    ]

    conflicts = [
        item
        for item in results
        if item[0] == "conflict"
    ]

    errors = [
        item
        for item in results
        if item[0] == "error"
    ]

    assert errors == []
    assert len(winners) == 1
    assert len(conflicts) == 3

    registry = json.loads(
        (
            tmp_path / "replay.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert len(
        registry["records"]
    ) == 1

    assert (
        registry["records"][0]["state"]
        == "claimed_dormant"
    )


def test_c8_4b4_record_persists_exact_ace_and_dacl(
    tmp_path,
    envelope_builder,
):
    result = claim(
        tmp_path
    )

    registry = json.loads(
        (
            tmp_path / "replay.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    record = (
        registry["records"][0]
    )

    assert record[
        "principal_dn"
    ] == PRINCIPAL_DN

    assert record[
        "principal_sid"
    ] == PRINCIPAL_SID

    assert record[
        "access_control_type"
    ] == "Allow"

    assert record[
        "rights"
    ] == [
        "ReadProperty",
        "WriteProperty",
    ]

    assert record[
        "inheritance_type"
    ] == "Descendents"

    assert (
        record["object_type_guid"]
        is None
    )

    assert (
        record[
            "inherited_object_type_guid"
        ]
        is None
    )

    assert record[
        "dacl_sddl_sha256"
    ] == result.dacl_sddl_sha256

    assert record[
        "acl_fingerprint"
    ] == result.acl_fingerprint


def test_c8_4b4_corrupt_claim_record_fails_closed(
    tmp_path,
    envelope_builder,
):
    claim(
        tmp_path
    )

    registry_path = (
        tmp_path / "replay.json"
    )

    registry = json.loads(
        registry_path.read_text(
            encoding="utf-8"
        )
    )

    del registry[
        "records"
    ][0]["actor_subject"]

    registry_path.write_text(
        json.dumps(
            registry
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        AclDelegationWriteReplayStorageError,
        match="incomplet",
    ):
        claim(
            tmp_path
        )


def test_c8_4b4_authorizing_claim_record_fails_closed(
    tmp_path,
    envelope_builder,
):
    claim(
        tmp_path
    )

    registry_path = (
        tmp_path / "replay.json"
    )

    registry = json.loads(
        registry_path.read_text(
            encoding="utf-8"
        )
    )

    registry[
        "records"
    ][0][
        "production_authorized"
    ] = True

    registry_path.write_text(
        json.dumps(
            registry
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        AclDelegationWriteReplayStorageError,
        match="autorisant",
    ):
        claim(
            tmp_path
        )


def test_c8_4b4_registry_symlink_fails_closed(
    tmp_path,
    envelope_builder,
):
    target = (
        tmp_path / "real-registry.json"
    )

    target.write_text(
        json.dumps({
            "contract_version": "c8.4b2",
            "records": [],
        }),
        encoding="utf-8",
    )

    (
        tmp_path / "replay.json"
    ).symlink_to(
        target
    )

    with pytest.raises(
        AclDelegationWriteReplayStorageError,
        match="symbolique",
    ):
        claim(
            tmp_path
        )


def test_c8_4b4_fresh_validation_occurs_under_lock():
    source = Path(
        "api/app/services/"
        "acl_delegation_write_claim.py"
    ).read_text(
        encoding="utf-8"
    )

    start = source.index(
        "def claim_acl_delegation_write_intent("
    )

    end = source.index(
        "\ndef assert_acl_delegation_write_claim_invariants",
        start,
    )

    function_source = source[
        start:end
    ]

    lock_index = function_source.index(
        "with _exclusive_registry_lock"
    )

    envelope_index = function_source.index(
        "build_acl_delegation_write_identity_envelope"
    )

    assert lock_index < envelope_index
