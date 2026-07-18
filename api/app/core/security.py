from __future__ import annotations

import os
import secrets
import ssl
from dataclasses import dataclass
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

from app.core.config import API_KEY


OIDC_ISSUER = os.getenv(
    "EITAS_OIDC_ISSUER",
    "https://10.10.10.11:62443/auth/realms/eitas",
).rstrip("/")

OIDC_JWKS_URL = os.getenv(
    "EITAS_OIDC_JWKS_URL",
    f"{OIDC_ISSUER}/protocol/openid-connect/certs",
)

OIDC_CA_CERT = os.getenv(
    "EITAS_OIDC_CA_CERT",
    "/etc/eitas-api/pki/eitas-root-ca.crt",
)

OIDC_ALLOWED_AZP = frozenset(
    value.strip()
    for value in os.getenv("EITAS_OIDC_ALLOWED_AZP", "eitas-portal").split(",")
    if value.strip()
)

OIDC_AUDIENCE = os.getenv("EITAS_OIDC_AUDIENCE", "").strip() or None
OIDC_ALGORITHMS = ("RS256",)
OIDC_LEEWAY_SECONDS = 30


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    auth_type: str
    subject: str
    username: str
    roles: frozenset[str]
    claims: dict[str, Any]


def _authentication_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _authorization_error(detail: str) -> HTTPException:
    return HTTPException(status_code=403, detail=detail)


@lru_cache(maxsize=1)
def _get_jwk_client() -> PyJWKClient:
    ssl_context = ssl.create_default_context(cafile=OIDC_CA_CERT)

    return PyJWKClient(
        OIDC_JWKS_URL,
        cache_keys=True,
        cache_jwk_set=True,
        lifespan=300,
        timeout=10,
        ssl_context=ssl_context,
    )


def _extract_roles(claims: dict[str, Any]) -> frozenset[str]:
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


def _validate_oidc_token(token: str) -> AuthenticatedIdentity:
    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)

        decode_options: dict[str, bool] = {
            "require": ["exp", "iat", "iss", "sub"],
            "verify_aud": OIDC_AUDIENCE is not None,
        }

        decode_arguments: dict[str, Any] = {
            "jwt": token,
            "key": signing_key.key,
            "algorithms": list(OIDC_ALGORITHMS),
            "issuer": OIDC_ISSUER,
            "leeway": OIDC_LEEWAY_SECONDS,
            "options": decode_options,
        }

        if OIDC_AUDIENCE is not None:
            decode_arguments["audience"] = OIDC_AUDIENCE

        claims = jwt.decode(**decode_arguments)

    except ExpiredSignatureError as exc:
        raise _authentication_error("Jeton OIDC expiré") from exc
    except PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="Service d’identité temporairement indisponible",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail="Configuration TLS du service d’identité indisponible",
        ) from exc
    except (InvalidTokenError, PyJWKClientError) as exc:
        raise _authentication_error("Jeton OIDC invalide") from exc

    authorized_party = claims.get("azp")

    if OIDC_ALLOWED_AZP and authorized_party not in OIDC_ALLOWED_AZP:
        raise _authentication_error("Client OIDC non autorisé")

    subject = claims.get("sub")
    username = (
        claims.get("preferred_username")
        or claims.get("email")
        or subject
    )

    if not isinstance(subject, str) or not subject:
        raise _authentication_error("Sujet OIDC manquant")

    if not isinstance(username, str) or not username:
        username = subject

    return AuthenticatedIdentity(
        auth_type="oidc",
        subject=subject,
        username=username,
        roles=_extract_roles(claims),
        claims=claims,
    )


def require_api_key(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> AuthenticatedIdentity:
    """
    Compatibilité transitoire du Pack B2.

    Priorité :
    1. Bearer OIDC pour le portail et les utilisateurs.
    2. X-API-Key pour les workers Windows existants.

    Le nom historique est conservé afin de ne pas modifier les 53 routes
    protégées pendant cette étape.
    """

    if authorization is not None:
        scheme, separator, credentials = authorization.partition(" ")

        if (
            separator != " "
            or scheme.lower() != "bearer"
            or not credentials.strip()
        ):
            raise _authentication_error(
                "En-tête Authorization invalide"
            )

        return _validate_oidc_token(credentials.strip())

    if x_api_key is not None:
        configured_api_key = str(API_KEY or "")

        if configured_api_key and secrets.compare_digest(
            x_api_key,
            configured_api_key,
        ):
            return AuthenticatedIdentity(
                auth_type="api_key",
                subject="worker-api-key",
                username="worker-api-key",
                roles=frozenset(),
                claims={},
            )

        raise _authentication_error("API key invalide")

    raise _authentication_error(
        "Authentification Bearer ou X-API-Key requise"
    )


require_authentication = require_api_key


def require_roles(*required_roles: str) -> Callable[..., AuthenticatedIdentity]:
    expected = frozenset(required_roles)

    def dependency(
        identity: AuthenticatedIdentity = Depends(require_api_key),
    ) -> AuthenticatedIdentity:
        # Cette fonction sera reliée aux routes dans le Pack B2.4.
        # Le corps explicite reste ici pour centraliser la règle RBAC.
        if not isinstance(identity, AuthenticatedIdentity):
            raise _authentication_error("Identité OIDC requise")

        if identity.auth_type != "oidc":
            raise _authorization_error("Authentification OIDC requise")

        if expected and identity.roles.isdisjoint(expected):
            raise _authorization_error("Rôle insuffisant")

        return identity

    return dependency


def require_roles_or_api_key(
    *required_roles: str,
) -> Callable[..., AuthenticatedIdentity]:
    """
    Autorise :
    - les workers authentifiés avec X-API-Key ;
    - les utilisateurs OIDC possédant au moins un rôle demandé.

    À utiliser uniquement pour les routes partagées entre le portail
    et les workers Windows.
    """

    expected = frozenset(required_roles)

    def dependency(
        identity: AuthenticatedIdentity = Depends(require_api_key),
    ) -> AuthenticatedIdentity:
        if not isinstance(identity, AuthenticatedIdentity):
            raise _authentication_error("Identité authentifiée requise")

        if identity.auth_type == "api_key":
            return identity

        if identity.auth_type != "oidc":
            raise _authorization_error(
                "Type d’authentification non autorisé"
            )

        if expected and identity.roles.isdisjoint(expected):
            raise _authorization_error("Rôle insuffisant")

        return identity

    return dependency
