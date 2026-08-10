from pathlib import Path


def test_activation_prepare_route_is_human_oidc_only():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    route = (
        '"/api/ad-explorer/recycle-bin/"\n'
        '    "activation-intent/prepare"'
    )

    assert route in source

    marker = (
        "def "
        "prepare_ad_recycle_bin_activation_intent_route"
    )

    start = source.index(
        marker
    )

    end = source.find(
        "\n@app.",
        start,
    )

    if end < 0:
        end = len(
            source
        )

    body = source[
        start:end
    ]

    assert "identity=Depends(AD_ACCESS)" in body

    assert (
        "service_prepare_ad_recycle_bin_activation_intent"
        in body
    )

    assert "AD_EXPLORER_JOBS_FILE" in body

    assert (
        "ad-recycle-bin-activation-intents.json"
        in body
    )

    assert "write_audit_log" in body

    assert "Enable-ADOptionalFeature" not in body
    assert "Restore-ADObject" not in body

    assert "service_create_ad_admin_job" not in body
    assert "service_claim_ad_admin_job" not in body
