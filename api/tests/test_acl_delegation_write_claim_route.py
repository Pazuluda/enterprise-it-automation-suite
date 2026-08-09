from pathlib import Path


MAIN = Path(
    "api/main.py"
).read_text(
    encoding="utf-8"
)

ADMIN = Path(
    "api/app/services/ad_admin.py"
).read_text(
    encoding="utf-8"
)

WORKER = Path(
    "agent-windows/modules/"
    "EitasAdAdmin.ps1"
).read_text(
    encoding="utf-8"
)


ROUTE_MARKER = (
    '@app.post(\n'
    '    "/api/ad-admin/acl-delegation/'
    'write-intent/claim"\n'
    ')'
)


def route_source():
    start = MAIN.index(
        ROUTE_MARKER
    )

    end = MAIN.index(
        '@app.post("/api/ad-admin/jobs")',
        start,
    )

    return MAIN[start:end]


def test_c8_4b4_route_exists_and_uses_oidc_access():
    route = route_source()

    assert (
        "identity=Depends(AD_ACCESS)"
        in route
    )

    assert (
        "claim_acl_delegation_write_intent("
        in route
    )


def test_c8_4b4_route_uses_private_replay_registry():
    assert (
        'DATA_DIR / "acl-delegation-write-replay.json"'
        in MAIN
    )

    route = route_source()

    assert (
        "ACL_DELEGATION_WRITE_REPLAY_FILE"
        in route
    )


def test_c8_4b4_conflict_is_http_409():
    route = route_source()

    assert (
        "except AclDelegationWriteClaimConflict"
        in route
    )

    assert (
        "status_code=409"
        in route
    )


def test_c8_4b4_storage_failure_is_fail_closed():
    route = route_source()

    assert (
        "AclDelegationWriteReplayStorageError"
        in route
    )

    assert (
        "status_code=503"
        in route
    )


def test_c8_4b4_route_returns_non_authorizing_claim():
    route = route_source()

    assert (
        '"replay_consumed": True'
        in route
    )

    assert (
        '"job_creation_authorized": False'
        in route
    )

    assert (
        '"runtime_authorized": False'
        in route
    )

    assert (
        '"production_authorized": False'
        in route
    )

    assert (
        '"ad_write_authorized": False'
        in route
    )


def test_c8_4b4_does_not_open_generic_acl_runtime():
    assert "apply_acl_delegation" not in ADMIN
    assert "apply_acl_delegation" not in WORKER
