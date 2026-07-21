from __future__ import annotations

import os
import ssl
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException


# Variables minimales requises lors de l’import du module.
SYSTEM_CA = (
    ssl.get_default_verify_paths().cafile
    or "/etc/ssl/certs/ca-certificates.crt"
)

os.environ.setdefault(
    "EITAS_IDENTITY_UPDATE_OIDC_PROVIDERS",
    (
        "https://issuer-a.example/realms/eitas"
        "|https://issuer-a.example/realms/eitas/"
        "protocol/openid-connect/certs"
    ),
)
os.environ.setdefault(
    "EITAS_IDENTITY_UPDATE_OIDC_CA_CERT",
    SYSTEM_CA,
)
os.environ.setdefault(
    "EITAS_IDENTITY_UPDATE_OIDC_ALLOWED_AZP",
    "account-console",
)

# Variables utilisées par le module général app.core.security.
os.environ.setdefault(
    "EITAS_OIDC_ISSUER",
    "https://issuer-a.example/realms/eitas",
)
os.environ.setdefault(
    "EITAS_OIDC_JWKS_URL",
    (
        "https://issuer-a.example/realms/eitas/"
        "protocol/openid-connect/certs"
    ),
)
os.environ.setdefault(
    "EITAS_OIDC_CA_CERT",
    SYSTEM_CA,
)
os.environ.setdefault(
    "EITAS_OIDC_ALLOWED_AZP",
    "eitas-portal",
)

from app.core import identity_update_security as security


class _SigningKey:
    def __init__(self, key: object) -> None:
        self.key = key


class _FakeJwkClient:
    def __init__(self, key: object) -> None:
        self._key = key

    def get_signing_key_from_jwt(
        self,
        token: str,
    ) -> _SigningKey:
        del token
        return _SigningKey(self._key)


class IdentityUpdateProviderConfigurationTests(
    unittest.TestCase
):
    def test_legacy_single_provider_fallback(self) -> None:
        environment = {
            "EITAS_IDENTITY_UPDATE_OIDC_ISSUER":
                "https://legacy.example/realms/eitas/",
            "EITAS_IDENTITY_UPDATE_OIDC_JWKS_URL":
                "https://legacy.example/certs",
        }

        with patch.dict(
            os.environ,
            environment,
            clear=False,
        ):
            os.environ.pop(
                "EITAS_IDENTITY_UPDATE_OIDC_PROVIDERS",
                None,
            )

            providers = (
                security
                ._load_identity_update_oidc_providers()
            )

        self.assertEqual(
            providers,
            {
                "https://legacy.example/realms/eitas":
                    "https://legacy.example/certs",
            },
        )

    def test_multiple_providers_are_loaded(self) -> None:
        configured = (
            "https://a.example/realms/eitas/"
            "|https://a.example/certs,"
            "https://b.example/realms/eitas"
            "|https://b.example/certs"
        )

        with patch.dict(
            os.environ,
            {
                "EITAS_IDENTITY_UPDATE_OIDC_PROVIDERS":
                    configured,
            },
            clear=False,
        ):
            providers = (
                security
                ._load_identity_update_oidc_providers()
            )

        self.assertEqual(
            providers,
            {
                "https://a.example/realms/eitas":
                    "https://a.example/certs",
                "https://b.example/realms/eitas":
                    "https://b.example/certs",
            },
        )

    def test_malformed_provider_is_rejected(self) -> None:
        with patch.dict(
            os.environ,
            {
                "EITAS_IDENTITY_UPDATE_OIDC_PROVIDERS":
                    "https://issuer.example/realms/eitas",
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                security._load_identity_update_oidc_providers()

    def test_normalized_duplicate_issuer_is_rejected(
        self,
    ) -> None:
        configured = (
            "https://duplicate.example/realms/eitas/"
            "|https://duplicate.example/certs-a,"
            "https://duplicate.example/realms/eitas"
            "|https://duplicate.example/certs-b"
        )

        with patch.dict(
            os.environ,
            {
                "EITAS_IDENTITY_UPDATE_OIDC_PROVIDERS":
                    configured,
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                security._load_identity_update_oidc_providers()


class IdentityUpdateTokenValidationTests(
    unittest.TestCase
):
    ISSUER_A = "https://issuer-a.example/realms/eitas"
    ISSUER_B = "https://issuer-b.example/realms/eitas"

    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key_a = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        cls.private_key_b = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        cls.public_key_a = cls.private_key_a.public_key()
        cls.public_key_b = cls.private_key_b.public_key()

    def setUp(self) -> None:
        security.IDENTITY_UPDATE_OIDC_PROVIDERS = {
            self.ISSUER_A:
                "https://issuer-a.example/certs",
            self.ISSUER_B:
                "https://issuer-b.example/certs",
        }
        security.IDENTITY_UPDATE_OIDC_ALLOWED_AZP = (
            frozenset({"account-console"})
        )
        security.IDENTITY_UPDATE_OIDC_AUDIENCE = None
        security._get_identity_update_jwk_client.cache_clear()

    def _claims(
        self,
        issuer: str,
        *,
        azp: str = "account-console",
    ) -> dict[str, object]:
        now = datetime.now(timezone.utc)

        return {
            "iss": issuer,
            "sub": "user-123",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "azp": azp,
            "preferred_username": "eitas-admin",
            "realm_access": {
                "roles": [
                    "UltraAdmin",
                    "Viewer",
                ],
            },
        }

    def _rs256_token(
        self,
        issuer: str,
        private_key: object,
        *,
        azp: str = "account-console",
    ) -> str:
        return jwt.encode(
            self._claims(
                issuer,
                azp=azp,
            ),
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

    def test_valid_token_is_accepted_for_each_issuer(
        self,
    ) -> None:
        cases = (
            (
                self.ISSUER_A,
                self.private_key_a,
                self.public_key_a,
            ),
            (
                self.ISSUER_B,
                self.private_key_b,
                self.public_key_b,
            ),
        )

        for issuer, private_key, public_key in cases:
            with self.subTest(issuer=issuer):
                token = self._rs256_token(
                    issuer,
                    private_key,
                )

                fake_client = _FakeJwkClient(public_key)

                with patch.object(
                    security,
                    "_get_identity_update_jwk_client",
                    return_value=fake_client,
                ) as client_factory:
                    identity = (
                        security
                        ._validate_identity_update_token(
                            token
                        )
                    )

                client_factory.assert_called_once_with(
                    issuer
                )
                self.assertEqual(
                    identity.auth_type,
                    "identity-update-oidc",
                )
                self.assertEqual(
                    identity.subject,
                    "user-123",
                )
                self.assertEqual(
                    identity.username,
                    "eitas-admin",
                )
                self.assertIn(
                    "UltraAdmin",
                    identity.roles,
                )

    def test_unknown_issuer_is_rejected_before_jwks(
        self,
    ) -> None:
        token = self._rs256_token(
            "https://unknown.example/realms/eitas",
            self.private_key_a,
        )

        with patch.object(
            security,
            "_get_identity_update_jwk_client",
        ) as client_factory:
            with self.assertRaises(HTTPException) as error:
                security._validate_identity_update_token(
                    token
                )

        self.assertEqual(
            error.exception.status_code,
            401,
        )
        client_factory.assert_not_called()

    def test_wrong_signature_is_rejected(self) -> None:
        token = self._rs256_token(
            self.ISSUER_A,
            self.private_key_b,
        )

        fake_client = _FakeJwkClient(
            self.public_key_a
        )

        with patch.object(
            security,
            "_get_identity_update_jwk_client",
            return_value=fake_client,
        ):
            with self.assertRaises(HTTPException) as error:
                security._validate_identity_update_token(
                    token
                )

        self.assertEqual(
            error.exception.status_code,
            401,
        )

    def test_non_rs256_algorithm_is_rejected(self) -> None:
        token = jwt.encode(
            self._claims(self.ISSUER_A),
            b"x" * 64,
            algorithm="HS256",
            headers={"kid": "test-key"},
        )

        fake_client = _FakeJwkClient(
            self.public_key_a
        )

        with patch.object(
            security,
            "_get_identity_update_jwk_client",
            return_value=fake_client,
        ):
            with self.assertRaises(HTTPException) as error:
                security._validate_identity_update_token(
                    token
                )

        self.assertEqual(
            error.exception.status_code,
            401,
        )

    def test_unauthorized_azp_is_rejected(self) -> None:
        token = self._rs256_token(
            self.ISSUER_A,
            self.private_key_a,
            azp="untrusted-client",
        )

        fake_client = _FakeJwkClient(
            self.public_key_a
        )

        with patch.object(
            security,
            "_get_identity_update_jwk_client",
            return_value=fake_client,
        ):
            with self.assertRaises(HTTPException) as error:
                security._validate_identity_update_token(
                    token
                )

        self.assertEqual(
            error.exception.status_code,
            401,
        )

    def test_required_role_is_enforced(self) -> None:
        identity = security.AuthenticatedIdentity(
            auth_type="identity-update-oidc",
            subject="user-123",
            username="eitas-admin",
            roles=frozenset({"Viewer"}),
            claims={},
        )

        dependency = (
            security.require_identity_update_roles(
                "UltraAdmin"
            )
        )

        with self.assertRaises(HTTPException) as error:
            dependency(identity)

        self.assertEqual(
            error.exception.status_code,
            403,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
