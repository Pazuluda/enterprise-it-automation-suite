from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from app.core.security import (
    AuthenticatedIdentity,
    OIDC_ALLOWED_AZP,
    OIDC_ISSUER,
)

from app.services.ad_recycle_bin_activation_prepare import (
    AdRecycleBinActivationPrepareError,
    prepare_ad_recycle_bin_activation_intent,
)


NOW = datetime(
    2026,
    8,
    10,
    15,
    45,
    tzinfo=timezone.utc,
)


def allowed_azp() -> str:
    if OIDC_ALLOWED_AZP:
        return sorted(
            OIDC_ALLOWED_AZP
        )[0]

    return "eitas-portal"


def identity(
    *,
    auth_type="oidc",
    subject="subject-c9",
    username="admin-c9",
    roles=None,
    claim_subject=None,
    issuer=None,
    azp=None,
):
    return AuthenticatedIdentity(
        auth_type=auth_type,
        subject=subject,
        username=username,
        roles=(
            frozenset(
                {"ADAdmin"}
            )
            if roles is None
            else frozenset(
                roles
            )
        ),
        claims={
            "sub":
                (
                    subject
                    if claim_subject is None
                    else claim_subject
                ),

            "iss":
                (
                    OIDC_ISSUER
                    if issuer is None
                    else issuer
                ),

            "azp":
                (
                    allowed_azp()
                    if azp is None
                    else azp
                ),
        },
    )


def payload():
    return {
        "evidence_job_id":
            "evidence-job-1",

        "forest_name":
            "API.LOCAL",

        "acknowledge_forest_wide":
            True,

        "acknowledge_irreversible":
            True,

        "acknowledge_no_restore":
            True,

        "requested_reason":
            "C9.3 dormant preparation test",
    }


def result(
    *,
    evidence_created_at=None,
):
    return {
        "action":
            "get_recycle_bin_activation_evidence",

        "read_only":
            True,

        "forest_name":
            "API.LOCAL",

        "root_domain":
            "API.LOCAL",

        "forest_mode":
            "Windows2025Forest",

        "recycle_bin_enabled":
            False,

        "recycle_bin_enabled_scope_count":
            0,

        "domain_controller_count":
            1,

        "replication_query_succeeded":
            True,

        "replication_partner_query_succeeded":
            True,

        "replication_failure_count":
            0,

        "replication_partner_count":
            0,

        "replication_ready":
            True,

        "evidence_created_at":
            (
                NOW.isoformat()
                if evidence_created_at is None
                else evidence_created_at
            ),

        "activation_authorized":
            False,

        "runtime_authorized":
            False,

        "production_authorized":
            False,

        "restore_authorized":
            False,

        "write_performed":
            False,
    }


def write_jobs(
    path: Path,
    *,
    job_result=None,
    status="completed",
    success=True,
    action="get_recycle_bin_activation_evidence",
):
    path.write_text(
        json.dumps(
            [
                {
                    "id":
                        "evidence-job-1",

                    "type":
                        "ad_explorer",

                    "status":
                        status,

                    "success":
                        success,

                    "action":
                        action,

                    "result":
                        (
                            result()
                            if job_result is None
                            else job_result
                        ),
                }
            ]
        ),
        encoding="utf-8",
    )


def prepare(
    tmp_path: Path,
    *,
    request_payload=None,
    actor=None,
    job_result=None,
    status="completed",
    success=True,
    action="get_recycle_bin_activation_evidence",
    mode="Simulation",
):
    jobs = (
        tmp_path
        / "ad-explorer-jobs.json"
    )

    storage = (
        tmp_path
        / "activation-intents.json"
    )

    write_jobs(
        jobs,
        job_result=job_result,
        status=status,
        success=success,
        action=action,
    )

    response, audit = (
        prepare_ad_recycle_bin_activation_intent(
            jobs,
            storage,
            (
                payload()
                if request_payload is None
                else request_payload
            ),
            identity=(
                identity()
                if actor is None
                else actor
            ),
            current_mode=mode,
            now=NOW,
        )
    )

    return (
        response,
        audit,
        storage,
    )


def test_valid_prepare_is_dormant(
    tmp_path: Path,
):
    response, audit, storage = prepare(
        tmp_path
    )

    assert response["state"] == (
        "activation_intent_dormant"
    )

    assert response["status"] == "dormant"

    assert response[
        "activation_authorized"
    ] is False

    assert response[
        "runtime_authorized"
    ] is False

    assert response[
        "production_authorized"
    ] is False

    assert response[
        "restore_authorized"
    ] is False

    assert response[
        "write_performed"
    ] is False

    assert response[
        "evidence_job_id"
    ] == "evidence-job-1"

    assert audit["actor"] == "admin-c9"

    data = json.loads(
        storage.read_text(
            encoding="utf-8"
        )
    )

    assert len(
        data["records"]
    ) == 1

    assert (
        data["records"][0]["status"]
        == "dormant"
    )


def test_client_identity_spoofing_is_rejected(
    tmp_path: Path,
):
    request = payload()
    request["actor_subject"] = "spoofed"

    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="Unknown preparation fields",
    ):
        prepare(
            tmp_path,
            request_payload=request,
        )


def test_client_server_evidence_spoofing_is_rejected(
    tmp_path: Path,
):
    request = payload()
    request["replication_ready"] = True

    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="Unknown preparation fields",
    ):
        prepare(
            tmp_path,
            request_payload=request,
        )


def test_non_oidc_actor_is_rejected(
    tmp_path: Path,
):
    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="OIDC authentication is required",
    ):
        prepare(
            tmp_path,
            actor=identity(
                auth_type="api_key"
            ),
        )


def test_insufficient_role_is_rejected(
    tmp_path: Path,
):
    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="ADAdmin or UltraAdmin",
    ):
        prepare(
            tmp_path,
            actor=identity(
                roles={"Viewer"}
            ),
        )


def test_oidc_subject_mismatch_is_rejected(
    tmp_path: Path,
):
    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="OIDC subject mismatch",
    ):
        prepare(
            tmp_path,
            actor=identity(
                claim_subject="other-subject"
            ),
        )


def test_wrong_evidence_action_is_rejected(
    tmp_path: Path,
):
    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="Evidence job action is invalid",
    ):
        prepare(
            tmp_path,
            action="get_deleted_objects",
        )


def test_unfinished_evidence_job_is_rejected(
    tmp_path: Path,
):
    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="not completed",
    ):
        prepare(
            tmp_path,
            status="processing",
        )


def test_failed_evidence_job_is_rejected(
    tmp_path: Path,
):
    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="did not succeed",
    ):
        prepare(
            tmp_path,
            success=False,
        )


def test_non_read_only_evidence_is_rejected(
    tmp_path: Path,
):
    unsafe = result()
    unsafe["read_only"] = False

    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="not read-only",
    ):
        prepare(
            tmp_path,
            job_result=unsafe,
        )


def test_unsafe_authorization_flag_is_rejected(
    tmp_path: Path,
):
    unsafe = result()
    unsafe["activation_authorized"] = True

    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="Unsafe evidence flag",
    ):
        prepare(
            tmp_path,
            job_result=unsafe,
        )


def test_recycle_bin_already_enabled_is_rejected(
    tmp_path: Path,
):
    enabled = result()
    enabled["recycle_bin_enabled"] = True

    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="must still be disabled",
    ):
        prepare(
            tmp_path,
            job_result=enabled,
        )


def test_replication_not_ready_is_rejected(
    tmp_path: Path,
):
    unhealthy = result()
    unhealthy["replication_ready"] = False

    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="Replication is not ready",
    ):
        prepare(
            tmp_path,
            job_result=unhealthy,
        )


def test_stale_evidence_is_rejected(
    tmp_path: Path,
):
    stale = result(
        evidence_created_at=(
            NOW
            - timedelta(
                seconds=301
            )
        ).isoformat()
    )

    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="Server evidence is stale",
    ):
        prepare(
            tmp_path,
            job_result=stale,
        )


def test_production_mode_is_rejected(
    tmp_path: Path,
):
    with pytest.raises(
        AdRecycleBinActivationPrepareError,
        match="only in Simulation mode",
    ):
        prepare(
            tmp_path,
            mode="Production",
        )
