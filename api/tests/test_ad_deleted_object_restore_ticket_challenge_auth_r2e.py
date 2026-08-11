from __future__ import annotations

from pathlib import Path
import re

import pytest

from fastapi import HTTPException

import main as api_main

from app.core.security import (
    AuthenticatedIdentity,
)


ISSUER = (
    "https://10.10.10.11:62443/"
    "auth/realms/eitas"
)

AZP = "eitas-portal"


def _oidc_identity(
    *roles: str,
    issuer: str = ISSUER,
    azp: str = AZP,
) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        auth_type="oidc",
        subject="c95-r2e-subject",
        username="c95-r2e-admin",
        roles=frozenset(
            roles
        ),
        claims={
            "iss":
                issuer,

            "azp":
                azp,

            "sub":
                "c95-r2e-subject",

            "preferred_username":
                "c95-r2e-admin",
        },
    )


def test_ticket_challenge_route_uses_oidc_only_ad_access():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        '"/api/ad-admin/'
        'deleted-object-restore/'
        'ticket-challenge"'
    )

    assert source.count(
        marker
    ) == 1

    start = source.index(
        marker
    )

    route = source[
        start:
        start + 3600
    ]

    assert (
        "identity=Depends(AD_ACCESS)"
        in route
    )

    assert (
        "require_roles_or_api_key"
        not in route
    )

    assert (
        "SECURITY_OR_API_KEY_ACCESS"
        not in route
    )

    assert (
        "AGENT_MODE_READ_OR_API_KEY_ACCESS"
        not in route
    )

    assert (
        "Depends(require_api_key)"
        not in route
    )


def test_ad_access_accepts_adadmin():
    identity = _oidc_identity(
        "ADAdmin"
    )

    assert (
        api_main.AD_ACCESS(
            identity=identity
        )
        is identity
    )


def test_ad_access_accepts_ultraadmin():
    identity = _oidc_identity(
        "UltraAdmin"
    )

    assert (
        api_main.AD_ACCESS(
            identity=identity
        )
        is identity
    )


@pytest.mark.parametrize(
    "role",
    [
        "Viewer",
        "Operator",
        "SecurityAdmin",
        "Auditor",
    ],
)
def test_other_portal_roles_cannot_create_restore_challenge(
    role: str,
):
    identity = _oidc_identity(
        role
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        api_main.AD_ACCESS(
            identity=identity
        )

    assert (
        captured.value.status_code
        == 403
    )

    assert (
        captured.value.detail
        == "Rôle insuffisant"
    )


def test_worker_api_key_identity_cannot_create_restore_challenge():
    worker = AuthenticatedIdentity(
        auth_type="api_key",
        subject="worker-api-key",
        username="worker-api-key",
        roles=frozenset(),
        claims={},
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        api_main.AD_ACCESS(
            identity=worker
        )

    assert (
        captured.value.status_code
        == 403
    )

    assert (
        captured.value.detail
        == "Authentification OIDC requise"
    )


def test_unknown_authentication_type_is_rejected():
    identity = AuthenticatedIdentity(
        auth_type="unknown",
        subject="subject",
        username="username",
        roles=frozenset(
            {
                "UltraAdmin",
            }
        ),
        claims={},
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        api_main.AD_ACCESS(
            identity=identity
        )

    assert (
        captured.value.status_code
        == 403
    )

    assert (
        captured.value.detail
        == "Authentification OIDC requise"
    )


def test_controlled_restore_actor_is_server_derived_from_oidc():
    identity = _oidc_identity(
        "ADAdmin"
    )

    actor = (
        api_main
        ._eitas_controlled_restore_oidc_actor(
            identity
        )
    )

    assert actor == {
        "subject":
            "c95-r2e-subject",

        "username":
            "c95-r2e-admin",

        "issuer":
            ISSUER,

        "azp":
            AZP,
    }


@pytest.mark.parametrize(
    "issuer,azp",
    [
        (
            "",
            AZP,
        ),
        (
            ISSUER,
            "",
        ),
    ],
)
def test_controlled_restore_actor_rejects_incomplete_oidc_binding(
    issuer: str,
    azp: str,
):
    identity = _oidc_identity(
        "UltraAdmin",
        issuer=issuer,
        azp=azp,
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        (
            api_main
            ._eitas_controlled_restore_oidc_actor(
                identity
            )
        )

    assert (
        captured.value.status_code
        == 400
    )

    assert (
        "OIDC incomplete"
        in captured.value.detail
    )


def test_ad_access_definition_remains_adadmin_ultraadmin_only():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    expected = '''AD_ACCESS = require_roles(
    "ADAdmin",
    "UltraAdmin",
)
'''

    assert expected in source

    match = re.search(
        r"(?m)^AD_ACCESS = require_roles\(\n"
        r"(?:    .*\n)*?"
        r"\)",
        source,
    )

    assert match is not None

    definition = match.group(
        0
    )

    assert definition == expected.rstrip()

    assert '"ADAdmin"' in definition
    assert '"UltraAdmin"' in definition

    for forbidden in (
        '"Viewer"',
        '"Operator"',
        '"SecurityAdmin"',
        '"Auditor"',
    ):
        assert forbidden not in definition
