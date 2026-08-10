from __future__ import annotations

import dataclasses
import hashlib
import json

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.security import OIDC_ALLOWED_AZP, OIDC_ISSUER
from app.services.ad_deleted_object_restore_authorization import (
    AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONTRACT_VERSION,
    AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_TTL_SECONDS,
    AdDeletedObjectRestoreAuthorization,
    assert_ad_deleted_object_restore_authorization_invariants,
)
from app.services.ad_deleted_object_restore_authorization_persistence import (
    AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION,
    AdDeletedObjectRestoreAuthorizationPersistenceError,
    assert_ad_deleted_object_restore_authorization_persistence_invariants,
    persist_ad_deleted_object_restore_authorization,
)


def _sha(payload: dict) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _azp() -> str:
    value = OIDC_ALLOWED_AZP
    if isinstance(value, str):
        return value
    if value:
        return sorted(value)[0]
    return "eitas-portal"


def _authorization(now: datetime) -> AdDeletedObjectRestoreAuthorization:
    payload = {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONTRACT_VERSION,
        "authorization_id": str(uuid4()),
        "state": "restore_authorization_dormant",
        "status": "authorized",
        "ticket_id": str(uuid4()),
        "ticket_digest": "a" * 64,
        "consumption_id": str(uuid4()),
        "consumption_record_digest": "b" * 64,
        "source_simulation_job_id": str(uuid4()),
        "source_inventory_job_id": str(uuid4()),
        "source_live_job_id": str(uuid4()),
        "fresh_live_job_id": str(uuid4()),
        "fresh_live_sha256": "c" * 64,
        "object_guid": str(uuid4()),
        "object_class": "group",
        "class_policy": "standard_controlled",
        "effective_new_name": "GG_C95_RECYCLE_TEST",
        "effective_target_path":
            "OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL",
        "actor_subject": "c9.5-test-subject",
        "actor_username": "c9.5-test-user",
        "actor_issuer": OIDC_ISSUER,
        "actor_azp": _azp(),
        "acknowledge_exact_object": True,
        "acknowledge_exact_target": True,
        "acknowledge_restore_write": True,
        "authorization_reason":
            "Validation C9.5 de la persistance dormante.",
        "issued_at": now.isoformat(),
        "expires_at": (
            now
            + timedelta(
                seconds=AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_TTL_SECONDS
            )
        ).isoformat(),
        "one_shot_required": True,
        "authorization_consumed": False,
        "human_authorized": True,
        "persistence_enabled": False,
        "route_enabled": False,
        "job_creation_authorized": False,
        "claim_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "restore_authorized": False,
        "restore_whatif_authorized": False,
        "execution_authorized": False,
        "write_performed": False,
    }
    authorization = AdDeletedObjectRestoreAuthorization(
        authorization_digest=_sha(payload),
        **payload,
    )
    assert_ad_deleted_object_restore_authorization_invariants(
        authorization
    )
    return authorization


def test_persist_authorization_is_dormant_and_0600(tmp_path: Path):
    now = datetime.now(timezone.utc)
    authorization = _authorization(now)
    storage = tmp_path / "restore-authorization-registry.json"

    record = persist_ad_deleted_object_restore_authorization(
        authorization,
        registry_file=storage,
        now=now + timedelta(seconds=1),
    )

    assert record.contract_version == (
        AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION
    )
    assert record.authorization_id == authorization.authorization_id
    assert record.state == "restore_authorization_dormant"
    assert record.status == "authorized"
    assert record.one_shot_required is True
    assert record.authorization_consumed is False
    assert record.human_authorized is True
    assert record.persistence_enabled is True
    assert record.route_enabled is False
    assert record.job_creation_authorized is False
    assert record.claim_authorized is False
    assert record.runtime_authorized is False
    assert record.production_authorized is False
    assert record.restore_authorized is False
    assert record.restore_whatif_authorized is False
    assert record.execution_authorized is False
    assert record.write_performed is False

    assert storage.exists()
    assert (storage.stat().st_mode & 0o777) == 0o600

    data = json.loads(storage.read_text(encoding="utf-8"))
    assert data["contract_version"] == (
        AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION
    )
    assert len(data["records"]) == 1

    assert_ad_deleted_object_restore_authorization_persistence_invariants(
        record
    )


def test_persistence_preserves_exact_restore_binding(tmp_path: Path):
    now = datetime.now(timezone.utc)
    authorization = _authorization(now)

    record = persist_ad_deleted_object_restore_authorization(
        authorization,
        registry_file=tmp_path / "registry.json",
        now=now + timedelta(seconds=1),
    )

    for field in (
        "ticket_id",
        "ticket_digest",
        "consumption_id",
        "consumption_record_digest",
        "source_simulation_job_id",
        "source_inventory_job_id",
        "source_live_job_id",
        "fresh_live_job_id",
        "fresh_live_sha256",
        "object_guid",
        "object_class",
        "class_policy",
        "effective_new_name",
        "effective_target_path",
        "actor_subject",
        "actor_username",
        "actor_issuer",
        "actor_azp",
        "authorization_reason",
    ):
        assert getattr(record, field) == getattr(authorization, field)


def test_duplicate_authorization_rejected(tmp_path: Path):
    now = datetime.now(timezone.utc)
    authorization = _authorization(now)
    storage = tmp_path / "registry.json"

    persist_ad_deleted_object_restore_authorization(
        authorization,
        registry_file=storage,
        now=now + timedelta(seconds=1),
    )

    with pytest.raises(
        AdDeletedObjectRestoreAuthorizationPersistenceError
    ):
        persist_ad_deleted_object_restore_authorization(
            authorization,
            registry_file=storage,
            now=now + timedelta(seconds=2),
        )


def test_expired_authorization_rejected(tmp_path: Path):
    now = datetime.now(timezone.utc)
    authorization = _authorization(now)

    with pytest.raises(
        AdDeletedObjectRestoreAuthorizationPersistenceError
    ):
        persist_ad_deleted_object_restore_authorization(
            authorization,
            registry_file=tmp_path / "registry.json",
            now=now
            + timedelta(
                seconds=AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_TTL_SECONDS
            ),
        )


def test_relative_registry_path_rejected():
    now = datetime.now(timezone.utc)
    authorization = _authorization(now)

    with pytest.raises(
        AdDeletedObjectRestoreAuthorizationPersistenceError
    ):
        persist_ad_deleted_object_restore_authorization(
            authorization,
            registry_file=Path("relative-registry.json"),
            now=now + timedelta(seconds=1),
        )


def test_symlink_registry_path_rejected(tmp_path: Path):
    now = datetime.now(timezone.utc)
    authorization = _authorization(now)
    target = tmp_path / "real.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "registry.json"
    link.symlink_to(target)

    with pytest.raises(
        AdDeletedObjectRestoreAuthorizationPersistenceError
    ):
        persist_ad_deleted_object_restore_authorization(
            authorization,
            registry_file=link,
            now=now + timedelta(seconds=1),
        )


def test_persisted_record_rejects_restore_authorized(tmp_path: Path):
    now = datetime.now(timezone.utc)
    record = persist_ad_deleted_object_restore_authorization(
        _authorization(now),
        registry_file=tmp_path / "registry.json",
        now=now + timedelta(seconds=1),
    )
    unsafe = dataclasses.replace(record, restore_authorized=True)

    with pytest.raises(
        AdDeletedObjectRestoreAuthorizationPersistenceError
    ):
        assert_ad_deleted_object_restore_authorization_persistence_invariants(
            unsafe
        )


def test_persisted_record_rejects_execution_authorized(tmp_path: Path):
    now = datetime.now(timezone.utc)
    record = persist_ad_deleted_object_restore_authorization(
        _authorization(now),
        registry_file=tmp_path / "registry.json",
        now=now + timedelta(seconds=1),
    )
    unsafe = dataclasses.replace(record, execution_authorized=True)

    with pytest.raises(
        AdDeletedObjectRestoreAuthorizationPersistenceError
    ):
        assert_ad_deleted_object_restore_authorization_persistence_invariants(
            unsafe
        )


def test_persistence_source_contains_no_restore_cmdlet():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_authorization_persistence.py"
    ).read_text(encoding="utf-8")

    forbidden = "Restore" + "-ADObject"
    assert forbidden not in source
    assert (
        "AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_RESTORE_AUTHORIZED = False"
        in source
    )
    assert (
        "AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_RESTORE_WHATIF_AUTHORIZED = False"
        in source
    )
    assert (
        "AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_EXECUTION_AUTHORIZED = False"
        in source
    )
