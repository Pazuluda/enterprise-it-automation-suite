from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


def read_main():
    return (
        ROOT
        / "api"
        / "main.py"
    ).read_text(
        encoding="utf-8"
    )


def read_ad_admin():
    return (
        ROOT
        / "api"
        / "app"
        / "services"
        / "ad_admin.py"
    ).read_text(
        encoding="utf-8"
    )


def read_windows():
    return (
        ROOT
        / "agent-windows"
        / "modules"
        / "EitasAdAdmin.ps1"
    ).read_text(
        encoding="utf-8-sig",
        errors="replace",
    )


def test_human_prepare_route_exists_and_uses_ad_access():
    main = read_main()

    assert (
        '"/api/ad-explorer/deleted-objects/"'
        in main
    )

    assert (
        '"restore-simulation/prepare"'
        in main
    )

    assert (
        "identity=Depends(AD_ACCESS)"
        in main
    )


def test_route_uses_both_job_stores_and_agent_mode():
    main = read_main()

    assert (
        "service_create_deleted_object_restore_simulation_record("
        in main
    )

    assert (
        "AD_ADMIN_JOBS_FILE,"
        in main
    )

    assert (
        "AD_EXPLORER_JOBS_FILE,"
        in main
    )

    assert (
        "agent_mode=mode"
        in main
    )

    assert (
        "_eitas_agent_mode_load_config()"
        in main
    )


def test_client_created_by_is_overwritten_by_authenticated_actor():
    main = read_main()

    assert (
        'simulation_payload[\n'
        '        "created_by"\n'
        "    ] = _c9_authenticated_actor("
        in main
    )

    assert (
        "def _c9_authenticated_actor"
        in main
    )

    assert (
        '"preferred_username"'
        in main
    )


def test_route_writes_audit_event():
    main = read_main()

    assert (
        "write_audit_log(\n"
        "        **audit_event\n"
        "    )"
        in main
    )


def test_restore_action_stays_out_of_generic_and_windows_runtime():
    action = (
        "simulate_deleted_object_restore"
    )

    assert action not in read_ad_admin()

    windows = read_windows()

    dispatch_marker = (
        "function Invoke-EitasAdAdminJob {"
    )

    dispatch_start = windows.index(
        dispatch_marker
    )

    dispatch_end = windows.find(
        "\nfunction ",
        dispatch_start
        + len(dispatch_marker),
    )

    if dispatch_end == -1:
        dispatcher = windows[
            dispatch_start:
        ]
    else:
        dispatcher = windows[
            dispatch_start:dispatch_end
        ]

    assert action not in dispatcher


def test_route_does_not_add_restore_cmdlet():
    runtime = "\n".join([
        read_main(),
        read_ad_admin(),
        read_windows(),
    ])

    assert (
        "Restore-ADObject"
        not in runtime
    )

    assert (
        "Enable-ADOptionalFeature"
        not in runtime
    )
