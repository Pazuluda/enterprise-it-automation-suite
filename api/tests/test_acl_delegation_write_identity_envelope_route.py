from pathlib import Path


MAIN = Path(
    "api/main.py"
).read_text(
    encoding="utf-8"
)


def test_c8_4b3_route_is_oidc_protected():
    marker = (
        '@app.post(\n'
        '    "/api/ad-admin/acl-delegation/'
        'write-intent/identity-envelope"\n'
        ')'
    )

    assert marker in MAIN

    start = MAIN.index(marker)

    end = MAIN.index(
        '@app.post("/api/ad-admin/jobs")',
        start,
    )

    route = MAIN[start:end]

    assert "identity=Depends(AD_ACCESS)" in route

    assert (
        "build_acl_delegation_write_identity_envelope"
        in route
    )


def test_c8_4b3_route_does_not_use_client_created_by():
    start = MAIN.index(
        "/api/ad-admin/acl-delegation/"
        "write-intent/identity-envelope"
    )

    end = MAIN.index(
        '@app.post("/api/ad-admin/jobs")',
        start,
    )

    route = MAIN[start:end]

    assert 'payload.get("created_by")' not in route
    assert "envelope.actor_subject" in route
    assert "envelope.actor_username" in route


def test_c8_4b3_route_returns_non_authorizing_state():
    start = MAIN.index(
        "/api/ad-admin/acl-delegation/"
        "write-intent/identity-envelope"
    )

    end = MAIN.index(
        '@app.post("/api/ad-admin/jobs")',
        start,
    )

    route = MAIN[start:end]

    assert '"job_creation_authorized": False' in route
    assert '"runtime_authorized": False' in route
    assert '"production_authorized": False' in route
    assert '"ad_write_authorized": False' in route

    assert '"consumed": False' in route
    assert '"consumption_id": None' in route


def test_c8_4b3_route_does_not_create_ad_admin_job():
    start = MAIN.index(
        "/api/ad-admin/acl-delegation/"
        "write-intent/identity-envelope"
    )

    end = MAIN.index(
        '@app.post("/api/ad-admin/jobs")',
        start,
    )

    route = MAIN[start:end]

    assert "service_create_ad_admin_job" not in route
    assert "save_json" not in route
    assert "claim_ad_admin_job" not in route


def test_c8_4b3_does_not_enable_apply_action():
    admin = Path(
        "api/app/services/ad_admin.py"
    ).read_text(
        encoding="utf-8"
    )

    worker = Path(
        "agent-windows/modules/EitasAdAdmin.ps1"
    ).read_text(
        encoding="utf-8"
    )

    assert "apply_acl_delegation" not in admin
    assert "apply_acl_delegation" not in worker
