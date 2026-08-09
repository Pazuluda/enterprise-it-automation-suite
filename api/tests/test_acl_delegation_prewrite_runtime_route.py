from __future__ import annotations

import re
from pathlib import Path

from app.services.ad_admin import (
    ALLOWED_ACTIONS,
)
from app.services.acl_delegation_prewrite_runtime import (
    ACL_DELEGATION_PREWRITE_AD_WRITE_AUTHORIZED,
    ACL_DELEGATION_PREWRITE_AGENT_ENDPOINTS_ENABLED,
    ACL_DELEGATION_PREWRITE_APPLY_ENABLED,
    ACL_DELEGATION_PREWRITE_PRODUCTION_AUTHORIZED,
)


MAIN = Path(
    "api/main.py"
).read_text(
    encoding="utf-8"
)


def _route_block(
    function_name: str,
) -> str:
    pattern = (
        r"(?ms)^@app\."
        r".*?"
        r"^def "
        + re.escape(function_name)
        + r"\("
        r".*?"
        r"(?=^@app\.|\Z)"
    )

    match = re.search(
        pattern,
        MAIN,
    )

    assert match is not None

    return match.group(0)


def test_c8_4c5c2_three_agent_routes_exist():
    assert (
        '"/api/agent/acl-delegation/prewrite/pending"'
        in MAIN
    )

    assert (
        '"/api/agent/acl-delegation/prewrite/claim/{ticket_id}"'
        in MAIN
    )

    assert (
        '"/api/agent/acl-delegation/prewrite/result/{ticket_id}"'
        in MAIN
    )


def test_c8_4c5c2_agent_routes_require_api_key():
    for function_name in (
        "get_pending_acl_delegation_prewrite_tickets",
        "claim_acl_delegation_prewrite_ticket_api",
        "submit_acl_delegation_prewrite_result_api",
    ):
        block = _route_block(
            function_name
        )

        assert (
            "Depends(require_api_key)"
            in block
        )


def test_c8_4c5c2_claim_has_strict_client_fields():
    block = _route_block(
        "claim_acl_delegation_prewrite_ticket_api"
    )

    assert (
        'allowed_fields = {\n        "agent_name",\n    }'
        in block
    )

    assert (
        '"payload": execution.payload'
        in block
    )

    assert (
        '"prewrite_validation_runtime_authorized": True'
        in block
    )

    assert (
        '"runtime_authorized": False'
        in block
    )

    assert (
        '"production_authorized": False'
        in block
    )

    assert (
        '"ad_write_authorized": False'
        in block
    )


def test_c8_4c5c2_result_has_strict_client_fields():
    block = _route_block(
        "submit_acl_delegation_prewrite_result_api"
    )

    for field in (
        '"execution_id"',
        '"agent_name"',
        '"success"',
        '"result"',
        '"message"',
    ):
        assert field in block

    assert (
        "success is not True and success is not False"
        in block
    )


def test_c8_4c5c2_generic_actions_stay_closed():
    assert (
        "prevalidate_acl_delegation"
        not in ALLOWED_ACTIONS
    )

    assert (
        "apply_acl_delegation"
        not in ALLOWED_ACTIONS
    )


def test_c8_4c5c2_only_validation_transport_enabled():
    assert (
        ACL_DELEGATION_PREWRITE_AGENT_ENDPOINTS_ENABLED
        is True
    )

    assert (
        ACL_DELEGATION_PREWRITE_APPLY_ENABLED
        is False
    )

    assert (
        ACL_DELEGATION_PREWRITE_PRODUCTION_AUTHORIZED
        is False
    )

    assert (
        ACL_DELEGATION_PREWRITE_AD_WRITE_AUTHORIZED
        is False
    )
