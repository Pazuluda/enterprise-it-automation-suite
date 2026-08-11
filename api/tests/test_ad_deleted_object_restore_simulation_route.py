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


def test_route_keeps_restore_write_out_of_api_and_dispatcher():
    main = read_main()
    ad_admin = read_ad_admin()
    windows = read_windows()

    # C9.5 A5C authorizes exactly one isolated Windows
    # Restore-ADObject primitive, and only with -WhatIf.
    # The API/backend generic AD Admin path must still
    # contain no restore primitive.
    assert (
        "Restore-ADObject"
        not in main
    )

    assert (
        "Restore-ADObject"
        not in ad_admin
    )

    handler_name = (
        "Invoke-EitasAdAdmin"
        "DeletedObjectRestoreWhatIf"
    )

    handler_marker = (
        f"function {handler_name} {{"
    )

    assert handler_marker in windows

    handler_start = windows.index(
        handler_marker
    )

    handler_end = windows.find(
        "\nfunction ",
        handler_start + len(
            handler_marker
        ),
    )

    handler = windows[
        handler_start:
        handler_end
        if handler_end != -1
        else None
    ]

    assert (
        handler.count(
            "Restore-ADObject `"
        )
        == 1
    )

    assert (
        "-WhatIf `"
        in handler
    )

    assert (
        "-Confirm:$false `"
        in handler
    )

    assert (
        "restore_performed = $false"
        in handler
    )

    assert (
        "write_performed = $false"
        in handler
    )

    dispatcher_marker = (
        "function Invoke-EitasAdAdminJob {"
    )

    dispatcher_start = windows.index(
        dispatcher_marker
    )

    dispatcher_end = windows.find(
        "\nfunction ",
        dispatcher_start + len(
            dispatcher_marker
        ),
    )

    dispatcher = windows[
        dispatcher_start:
        dispatcher_end
        if dispatcher_end != -1
        else None
    ]

    assert (
        "Restore-ADObject"
        not in dispatcher
    )

    assert (
        handler_name
        not in dispatcher
    )

    assert (
        "restore_deleted_object_whatif"
        not in dispatcher
    )
