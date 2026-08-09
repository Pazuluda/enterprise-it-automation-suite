import json
import multiprocessing
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.acl_delegation_write_binding import (
    calculate_acl_fingerprint,
)
from app.services.acl_delegation_write_replay import (
    AclDelegationWriteReplayConflict,
    AclDelegationWriteReplayStorageError,
    consume_trusted_acl_delegation_write_evidence,
)


TARGET_DN = (
    "OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
)

SIMULATION_JOB_ID = (
    "7bf650bd-7799-499f-8e42-9973af0b6b0c"
)

SECURITY_JOB_ID = (
    "d519800a-0ccb-4a61-aab9-6c45c57fd190"
)

NOW = datetime(
    2026,
    8,
    9,
    14,
    39,
    0,
    tzinfo=timezone.utc,
)


def descriptor():
    return {
        "action": "get_security_descriptor",
        "object_dn": TARGET_DN,
        "object_guid": (
            "8838f739-c817-4b45-"
            "90b2-b597ce79312a"
        ),
        "dacl_fingerprint_version": (
            "sddl-access-sha256-v1"
        ),
        "dacl_sddl_sha256": "a" * 64,
        "read_only": True,
        "sacl_included": False,
        "inheritance_enabled": True,
        "access_rules_protected": False,
        "rules": [
            {
                "identity": "API\\Admins du domaine",
                "sid": "S-1-5-21-1-2-3-512",
                "access_control_type": "Allow",
                "active_directory_rights": "GenericAll",
                "inheritance_type": "None",
                "inheritance_flags": "None",
                "propagation_flags": "None",
                "is_inherited": False,
                "object_type_guid": (
                    "00000000-0000-0000-"
                    "0000-000000000000"
                ),
                "inherited_object_type_guid": (
                    "00000000-0000-0000-"
                    "0000-000000000000"
                ),
            },
        ],
    }


def simulation_job(
    job_id=SIMULATION_JOB_ID,
):
    return {
        "id": job_id,
        "action": "simulate_acl_delegation",
        "status": "completed",
        "success": True,
        "completed_at": (
            "2026-08-09T14:30:00Z"
        ),
        "payload": {
            "object_dn": TARGET_DN,
            "principal_identity": (
                "GG_IT_Admin"
            ),
            "access_control_type": "Allow",
            "rights": [
                "ReadProperty",
                "WriteProperty",
            ],
            "inheritance_type": "Descendents",
            "object_type_guid": None,
            "inherited_object_type_guid": None,
            "mode": "Simulation",
            "execution_policy": "simulation_only",
        },
        "output": {
            "action": "simulate_acl_delegation",
            "mode": "Simulation",
            "simulated": True,
            "write_performed": False,
            "production_authorized": False,
            "ad_write_authorized": False,
            "execution_policy": "simulation_only",
            "target": {
                "dn": TARGET_DN,
                "object_guid": (
                    "8838f739-c817-4b45-"
                    "90b2-b597ce79312a"
                ),
            },
            "principal": {
                "dn": (
                    "CN=GG_IT_Admin,"
                    "OU=Groups,OU=EITAS,"
                    "DC=API,DC=LOCAL"
                ),
                "sid": (
                    "S-1-5-21-1101651174-"
                    "4260486456-3261528239-1118"
                ),
            },
            "ace": {
                "access_control_type": "Allow",
                "rights": [
                    "ReadProperty",
                    "WriteProperty",
                ],
                "rights_mask": 48,
                "inheritance_type": "Descendents",
                "inheritance_value": 2,
                "object_type_guid": None,
                "inherited_object_type_guid": None,
            },
        },
    }


def security_job(
    job_id=SECURITY_JOB_ID,
):
    value = descriptor()

    return {
        "id": job_id,
        "action": "get_security_descriptor",
        "status": "completed",
        "success": True,
        "completed_at": (
            "2026-08-09T14:38:30Z"
        ),
        "output": deepcopy(value),
        "result": deepcopy(value),
    }


def intent_payload(
    simulation_id=SIMULATION_JOB_ID,
    security_id=SECURITY_JOB_ID,
):
    return {
        "action": "apply_acl_delegation",
        "mode": "Production",
        "object_dn": TARGET_DN,
        "principal_identity": (
            "GG_IT_Admin"
        ),
        "access_control_type": "Allow",
        "rights": [
            "ReadProperty",
            "WriteProperty",
        ],
        "inheritance_type": "Descendents",
        "object_type_guid": None,
        "inherited_object_type_guid": None,
        "simulation_job_id": simulation_id,
        "security_descriptor_job_id": (
            security_id
        ),
        "expected_acl_fingerprint": (
            calculate_acl_fingerprint(
                descriptor()
            )
        ),
        "confirm_object_dn": TARGET_DN,
        "confirmation_phrase": (
            "APPLY ACL DELEGATION"
        ),
    }


def write_stores(
    tmp_path,
    simulations=None,
    securities=None,
):
    admin = (
        tmp_path / "ad-admin-jobs.json"
    )

    explorer = (
        tmp_path / "ad-explorer-jobs.json"
    )

    registry = (
        tmp_path
        / "acl-write-consumption.json"
    )

    admin.write_text(
        json.dumps(
            simulations
            if simulations is not None
            else [simulation_job()]
        ),
        encoding="utf-8",
    )

    explorer.write_text(
        json.dumps(
            securities
            if securities is not None
            else [security_job()]
        ),
        encoding="utf-8",
    )

    return admin, explorer, registry


def consume(
    admin,
    explorer,
    registry,
    payload=None,
):
    return (
        consume_trusted_acl_delegation_write_evidence(
            ad_admin_jobs_file=admin,
            ad_explorer_jobs_file=explorer,
            replay_registry_file=registry,
            intent_payload=(
                payload
                if payload is not None
                else intent_payload()
            ),
            now=NOW,
        )
    )


def test_c8_4b2_consumes_once(
    tmp_path,
):
    admin, explorer, registry = (
        write_stores(tmp_path)
    )

    result = consume(
        admin,
        explorer,
        registry,
    )

    assert result.consumed is True
    assert len(result.consumption_id) == 36

    assert result.simulation_job_id == (
        SIMULATION_JOB_ID
    )

    assert (
        result.security_descriptor_job_id
        == SECURITY_JOB_ID
    )


def test_c8_4b2_remains_non_authorizing(
    tmp_path,
):
    admin, explorer, registry = (
        write_stores(tmp_path)
    )

    result = consume(
        admin,
        explorer,
        registry,
    )

    assert result.job_creation_authorized is False
    assert result.runtime_authorized is False
    assert result.production_authorized is False
    assert result.ad_write_authorized is False


def test_c8_4b2_rejects_exact_replay(
    tmp_path,
):
    admin, explorer, registry = (
        write_stores(tmp_path)
    )

    consume(
        admin,
        explorer,
        registry,
    )

    with pytest.raises(
        AclDelegationWriteReplayConflict
    ):
        consume(
            admin,
            explorer,
            registry,
        )


def test_c8_4b2_registry_is_private(
    tmp_path,
):
    admin, explorer, registry = (
        write_stores(tmp_path)
    )

    consume(
        admin,
        explorer,
        registry,
    )

    mode = (
        registry.stat().st_mode
        & 0o777
    )

    assert mode == 0o600

    lock = registry.with_name(
        "." + registry.name + ".lock"
    )

    lock_mode = (
        lock.stat().st_mode
        & 0o777
    )

    assert lock_mode == 0o600


def test_c8_4b2_registry_is_durable(
    tmp_path,
):
    admin, explorer, registry = (
        write_stores(tmp_path)
    )

    first = consume(
        admin,
        explorer,
        registry,
    )

    data = json.loads(
        registry.read_text(
            encoding="utf-8"
        )
    )

    assert data["contract_version"] == (
        "c8.4b2"
    )

    assert len(data["records"]) == 1

    record = data["records"][0]

    assert record["consumption_id"] == (
        first.consumption_id
    )

    assert record["state"] == "consumed"


def test_c8_4b2_corrupt_registry_fails_closed(
    tmp_path,
):
    admin, explorer, registry = (
        write_stores(tmp_path)
    )

    registry.write_text(
        "{broken",
        encoding="utf-8",
    )

    with pytest.raises(
        AclDelegationWriteReplayStorageError
    ):
        consume(
            admin,
            explorer,
            registry,
        )


def test_c8_4b2_wrong_registry_version_fails_closed(
    tmp_path,
):
    admin, explorer, registry = (
        write_stores(tmp_path)
    )

    registry.write_text(
        json.dumps({
            "contract_version": "old",
            "records": [],
        }),
        encoding="utf-8",
    )

    with pytest.raises(
        AclDelegationWriteReplayStorageError
    ):
        consume(
            admin,
            explorer,
            registry,
        )


def test_c8_4b2_registry_symlink_is_rejected(
    tmp_path,
):
    admin, explorer, registry = (
        write_stores(tmp_path)
    )

    victim = tmp_path / "victim.json"

    victim.write_text(
        "{}",
        encoding="utf-8",
    )

    registry.symlink_to(
        victim
    )

    with pytest.raises(
        AclDelegationWriteReplayStorageError
    ):
        consume(
            admin,
            explorer,
            registry,
        )

    assert victim.read_text(
        encoding="utf-8"
    ) == "{}"


def test_c8_4b2_reused_simulation_is_rejected(
    tmp_path,
):
    second_security_id = (
        "11111111-2222-4333-8444-555555555555"
    )

    admin, explorer, registry = write_stores(
        tmp_path,
        securities=[
            security_job(),
            security_job(
                second_security_id
            ),
        ],
    )

    consume(
        admin,
        explorer,
        registry,
    )

    second = intent_payload(
        simulation_id=SIMULATION_JOB_ID,
        security_id=second_security_id,
    )

    with pytest.raises(
        AclDelegationWriteReplayConflict,
        match="Simulation ACL deja consommee",
    ):
        consume(
            admin,
            explorer,
            registry,
            second,
        )


def test_c8_4b2_reused_descriptor_is_rejected(
    tmp_path,
):
    second_simulation_id = (
        "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    )

    admin, explorer, registry = write_stores(
        tmp_path,
        simulations=[
            simulation_job(),
            simulation_job(
                second_simulation_id
            ),
        ],
    )

    consume(
        admin,
        explorer,
        registry,
    )

    second = intent_payload(
        simulation_id=second_simulation_id,
        security_id=SECURITY_JOB_ID,
    )

    with pytest.raises(
        AclDelegationWriteReplayConflict,
        match=(
            "Security Descriptor deja consomme"
        ),
    ):
        consume(
            admin,
            explorer,
            registry,
            second,
        )


def _concurrent_consumer(
    admin,
    explorer,
    registry,
    barrier,
    queue,
):
    try:
        barrier.wait(
            timeout=10
        )

        result = (
            consume_trusted_acl_delegation_write_evidence(
                ad_admin_jobs_file=Path(admin),
                ad_explorer_jobs_file=Path(
                    explorer
                ),
                replay_registry_file=Path(
                    registry
                ),
                intent_payload=intent_payload(),
                now=NOW,
            )
        )

        queue.put(
            (
                "success",
                result.consumption_id,
            )
        )

    except AclDelegationWriteReplayConflict:
        queue.put(
            ("conflict", "")
        )

    except Exception as exc:
        queue.put(
            (
                "error",
                type(exc).__name__
                + ":"
                + str(exc),
            )
        )


@pytest.mark.skipif(
    os.name != "posix",
    reason="fcntl/flock requires POSIX",
)
def test_c8_4b2_interprocess_race_has_one_winner(
    tmp_path,
):
    admin, explorer, registry = (
        write_stores(tmp_path)
    )

    ctx = multiprocessing.get_context(
        "fork"
    )

    worker_count = 4

    barrier = ctx.Barrier(
        worker_count
    )

    queue = ctx.Queue()

    processes = [
        ctx.Process(
            target=_concurrent_consumer,
            args=(
                str(admin),
                str(explorer),
                str(registry),
                barrier,
                queue,
            ),
        )
        for _ in range(worker_count)
    ]

    for process in processes:
        process.start()

    for process in processes:
        process.join(
            timeout=15
        )

    for process in processes:
        assert not process.is_alive()
        assert process.exitcode == 0

    results = [
        queue.get(
            timeout=5
        )
        for _ in range(worker_count)
    ]

    successes = [
        item
        for item in results
        if item[0] == "success"
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
    assert len(successes) == 1
    assert len(conflicts) == 3

    data = json.loads(
        registry.read_text(
            encoding="utf-8"
        )
    )

    assert len(data["records"]) == 1


def test_c8_4b2_no_acl_write_primitive():
    source = Path(
        "api/app/services/"
        "acl_delegation_write_replay.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "Set-Acl",
        "SetAccessRule",
        "AddAccessRule",
        "RemoveAccessRule",
        "ResetAccessRule",
        "SetOwner",
        "ActiveDirectoryAccessRule",
    )

    for token in forbidden:
        assert token not in source
