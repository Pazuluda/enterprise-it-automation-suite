from __future__ import annotations

import os
import ssl
from functools import lru_cache
from typing import Any, Callable

import jwt
from fastapi import Depends, Header, HTTPException
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidTokenError,
    PyJWKClientConnectionError,
    PyJWKClientError,
)
from jwt.jwks_client import PyJWKClient

from app.core.security import AuthenticatedIdentity


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Variable obligatoire absente : {name}"
        )

    return value


def _load_identity_update_oidc_providers(
) -> dict[str, str]:
    configured = os.getenv(
        "EITAS_IDENTITY_UPDATE_OIDC_PROVIDERS",
        "",
    ).strip()

    if not configured:
        issuer = _required_environment(
            "EITAS_IDENTITY_UPDATE_OIDC_ISSUER"
        ).rstrip("/")

        jwks_url = _required_environment(
            "EITAS_IDENTITY_UPDATE_OIDC_JWKS_URL"
        )

        return {issuer: jwks_url}

    providers: dict[str, str] = {}

    for raw_entry in configured.split(","):
        raw_entry = raw_entry.strip()

        if not raw_entry:
            continue

        issuer, separator, jwks_url = (
            raw_entry.partition("|")
        )

        issuer = issuer.strip().rstrip("/")
        jwks_url = jwks_url.strip()

        if (
            separator != "|"
            or not issuer
            or not jwks_url
        ):
            raise RuntimeError(
                "Configuration invalide : "
                "EITAS_IDENTITY_UPDATE_OIDC_PROVIDERS"
            )

        if issuer in providers:
            raise RuntimeError(
                f"Émetteur OIDC dupliqué : {issuer}"
            )

        providers[issuer] = jwks_url

    if not providers:
        raise RuntimeError(
            "Aucun fournisseur OIDC autorisé"
        )

    return providers


IDENTITY_UPDATE_OIDC_PROVIDERS = (
    _load_identity_update_oidc_providers()
)

IDENTITY_UPDATE_OIDC_CA_CERT = (
    _required_environment(
        "EITAS_IDENTITY_UPDATE_OIDC_CA_CERT"
    )
)

IDENTITY_UPDATE_OIDC_ALLOWED_AZP = frozenset(
    value.strip()
    for value in _required_environment(
        "EITAS_IDENTITY_UPDATE_OIDC_ALLOWED_AZP"
    ).split(",")
    if value.strip()
)

IDENTITY_UPDATE_OIDC_AUDIENCE = (
    os.getenv(
        "EITAS_IDENTITY_UPDATE_OIDC_AUDIENCE",
        "",
    ).strip()
    or None
)

IDENTITY_UPDATE_OIDC_ALGORITHMS = ("RS256",)
IDENTITY_UPDATE_OIDC_LEEWAY_SECONDS = 30


def _authentication_error(
    detail: str,
) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _authorization_error(
    detail: str,
) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail=detail,
    )


@lru_cache(maxsize=8)
def _get_identity_update_jwk_client(
    issuer: str,
) -> PyJWKClient:
    jwks_url = IDENTITY_UPDATE_OIDC_PROVIDERS.get(
        issuer
    )

    if jwks_url is None:
        raise _authentication_error(
            "Émetteur EITAS Identity non autorisé"
        )

    ssl_context = ssl.create_default_context(
        cafile=IDENTITY_UPDATE_OIDC_CA_CERT
    )

    return PyJWKClient(
        jwks_url,
        cache_keys=True,
        cache_jwk_set=True,
        lifespan=300,
        timeout=10,
        ssl_context=ssl_context,
    )


def _extract_roles(
    claims: dict[str, Any],
) -> frozenset[str]:
    realm_access = claims.get("realm_access")

    if not isinstance(realm_access, dict):
        return frozenset()

    roles = realm_access.get("roles")

    if not isinstance(roles, list):
        return frozenset()

    return frozenset(
        role
        for role in roles
        if isinstance(role, str) and role
    )


def _validate_identity_update_token(
    token: str,
) -> AuthenticatedIdentity:
    try:
        unverified_claims = jwt.decode(
            token,
            algorithms=list(
                IDENTITY_UPDATE_OIDC_ALGORITHMS
            ),
            options={
                "verify_signature": False,
                "verify_aud": False,
            },
        )

        token_issuer = unverified_claims.get("iss")

        if (
            not isinstance(token_issuer, str)
            or token_issuer
            not in IDENTITY_UPDATE_OIDC_PROVIDERS
        ):
            raise _authentication_error(
                "Émetteur EITAS Identity non autorisé"
            )

        signing_key = (
            _get_identity_update_jwk_client(
                token_issuer
            )
            .get_signing_key_from_jwt(token)
        )

        options: dict[str, bool] = {
            "require": ["exp", "iat", "iss", "sub"],
            "verify_aud": (
                IDENTITY_UPDATE_OIDC_AUDIENCE
                is not None
            ),
        }

        arguments: dict[str, Any] = {
            "jwt": token,
            "key": signing_key.key,
            "algorithms": list(
                IDENTITY_UPDATE_OIDC_ALGORITHMS
            ),
            "issuer": token_issuer,
            "leeway": (
                IDENTITY_UPDATE_OIDC_LEEWAY_SECONDS
            ),
            "options": options,
        }

        if IDENTITY_UPDATE_OIDC_AUDIENCE is not None:
            arguments["audience"] = (
                IDENTITY_UPDATE_OIDC_AUDIENCE
            )

        claims = jwt.decode(**arguments)

    except ExpiredSignatureError as exc:
        raise _authentication_error(
            "Jeton EITAS Identity expiré"
        ) from exc
    except PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "EITAS Identity temporairement "
                "indisponible"
            ),
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Configuration TLS EITAS Identity "
                "indisponible"
            ),
        ) from exc
    except (
        InvalidTokenError,
        PyJWKClientError,
    ) as exc:
        raise _authentication_error(
            "Jeton EITAS Identity invalide"
        ) from exc

    authorized_party = claims.get("azp")

    if (
        IDENTITY_UPDATE_OIDC_ALLOWED_AZP
        and authorized_party
        not in IDENTITY_UPDATE_OIDC_ALLOWED_AZP
    ):
        raise _authentication_error(
            "Client EITAS Identity non autorisé"
        )

    subject = claims.get("sub")
    username = (
        claims.get("preferred_username")
        or claims.get("email")
        or subject
    )

    if not isinstance(subject, str) or not subject:
        raise _authentication_error(
            "Sujet EITAS Identity manquant"
        )

    if not isinstance(username, str) or not username:
        username = subject

    return AuthenticatedIdentity(
        auth_type="identity-update-oidc",
        subject=subject,
        username=username,
        roles=_extract_roles(claims),
        claims=claims,
    )


def require_identity_update_authentication(
    authorization: str | None = Header(
        default=None
    ),
) -> AuthenticatedIdentity:
    if authorization is None:
        raise _authentication_error(
            "Authentification Bearer EITAS Identity requise"
        )

    scheme, separator, credentials = (
        authorization.partition(" ")
    )

    if (
        separator != " "
        or scheme.lower() != "bearer"
        or not credentials.strip()
    ):
        raise _authentication_error(
            "En-tête Authorization invalide"
        )

    return _validate_identity_update_token(
        credentials.strip()
    )


def require_identity_update_roles(
    *required_roles: str,
) -> Callable[..., AuthenticatedIdentity]:
    expected = frozenset(required_roles)

    def dependency(
        identity: AuthenticatedIdentity = Depends(
            require_identity_update_authentication
        ),
    ) -> AuthenticatedIdentity:
        if (
            identity.auth_type
            != "identity-update-oidc"
        ):
            raise _authorization_error(
                "Authentification EITAS Identity requise"
            )

        if (
            expected
            and identity.roles.isdisjoint(expected)
        ):
            raise _authorization_error(
                "Rôle EITAS Identity insuffisant"
            )

        return identity

    return dependency
