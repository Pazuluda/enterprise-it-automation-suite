from __future__ import annotations

import fcntl
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


MAXIMUM_STATUS_SIZE = 256 * 1024


class IdentityUpdateStatusUnavailable(
    RuntimeError
):
    pass


def _text(
    mapping: dict[str, Any],
    key: str,
) -> str:
    value = mapping.get(key)

    if not isinstance(value, str) or not value.strip():
        raise IdentityUpdateStatusUnavailable(
            f"État de mise à jour invalide : {key}"
        )

    return value.strip()


def _boolean(
    mapping: dict[str, Any],
    key: str,
) -> bool:
    value = mapping.get(key)

    if not isinstance(value, bool):
        raise IdentityUpdateStatusUnavailable(
            f"État de mise à jour invalide : {key}"
        )

    return value


def _mapping(
    mapping: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    value = mapping.get(key)

    if not isinstance(value, dict):
        raise IdentityUpdateStatusUnavailable(
            f"État de mise à jour invalide : {key}"
        )

    return value


def _artifact(
    interfaces: dict[str, Any],
    name: str,
) -> dict[str, str]:
    value = _mapping(interfaces, name)

    version = _text(value, "version")
    sha256 = _text(value, "sha256").lower()

    if (
        len(sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in sha256
        )
    ):
        raise IdentityUpdateStatusUnavailable(
            f"SHA-256 invalide : {name}"
        )

    return {
        "version": version,
        "sha256": sha256,
    }


def get_identity_update_status(
    path: Path,
) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise IdentityUpdateStatusUnavailable(
            "État du moteur de mise à jour indisponible"
        ) from exc

    if stat.S_ISLNK(metadata.st_mode):
        raise IdentityUpdateStatusUnavailable(
            "État du moteur de mise à jour non fiable"
        )

    if not stat.S_ISREG(metadata.st_mode):
        raise IdentityUpdateStatusUnavailable(
            "État du moteur de mise à jour invalide"
        )

    if metadata.st_size > MAXIMUM_STATUS_SIZE:
        raise IdentityUpdateStatusUnavailable(
            "État du moteur de mise à jour trop volumineux"
        )

    try:
        document = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise IdentityUpdateStatusUnavailable(
            "État du moteur de mise à jour illisible"
        ) from exc

    if not isinstance(document, dict):
        raise IdentityUpdateStatusUnavailable(
            "État du moteur de mise à jour invalide"
        )

    if document.get("schema_version") != 1:
        raise IdentityUpdateStatusUnavailable(
            "Version du schéma de mise à jour invalide"
        )

    engine = _mapping(document, "engine")
    interfaces = _mapping(
        document,
        "interfaces",
    )
    source = _mapping(document, "source")
    production = _mapping(
        document,
        "production",
    )

    raw_stages = document.get("stages")

    if not isinstance(raw_stages, list):
        raise IdentityUpdateStatusUnavailable(
            "Étapes de mise à jour invalides"
        )

    stages: list[dict[str, str]] = []

    for raw_stage in raw_stages[:10]:
        if not isinstance(raw_stage, dict):
            raise IdentityUpdateStatusUnavailable(
                "Étape de mise à jour invalide"
            )

        stages.append(
            {
                "id": _text(raw_stage, "id"),
                "label": _text(
                    raw_stage,
                    "label",
                ),
                "state": _text(
                    raw_stage,
                    "state",
                ),
            }
        )

    return {
        "schema_version": 1,
        "status": _text(document, "status"),
        "environment": _text(
            document,
            "environment",
        ),
        "mode": _text(document, "mode"),
        "generated_at": _text(
            document,
            "generated_at",
        ),
        "engine": {
            "name": _text(engine, "name"),
            "version": _text(
                engine,
                "version",
            ),
            "upstream_tag": _text(
                engine,
                "upstream_tag",
            ),
            "upstream_commit": _text(
                engine,
                "upstream_commit",
            ),
        },
        "interfaces": {
            "account": _artifact(
                interfaces,
                "account",
            ),
            "admin": _artifact(
                interfaces,
                "admin",
            ),
            "login": _artifact(
                interfaces,
                "login",
            ),
        },
        "source": {
            "locked": _boolean(
                source,
                "locked",
            ),
            "verification": _text(
                source,
                "verification",
            ),
            "patch_policy": _text(
                source,
                "patch_policy",
            ),
        },
        "stages": stages,
        "production": {
            "automatic_updates": _boolean(
                production,
                "automatic_updates",
            ),
            "locked": _boolean(
                production,
                "locked",
            ),
        },
    }

class IdentityUpdateRequestConflict(RuntimeError):
    pass


class IdentityUpdateRequestError(RuntimeError):
    pass


def _utc_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def create_identity_update_source_check_request(
    path: Path,
    requested_by: str,
) -> dict[str, str]:
    actor = str(requested_by or "").strip()

    if not actor or len(actor) > 128:
        raise IdentityUpdateRequestError(
            "Identité de l’administrateur invalide"
        )

    request_id = str(uuid4())
    requested_at = _utc_iso()

    document = {
        "schema_version": 1,
        "action": "verify_upstream",
        "request_id": request_id,
        "requested_by": actor,
        "requested_at": requested_at,
    }

    lock_path = path.parent / ".source-check-request.lock"
    temporary = path.parent / (
        f".{path.name}.{request_id}.tmp"
    )

    try:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        lock_fd = os.open(
            lock_path,
            os.O_RDWR | os.O_CREAT,
            0o640,
        )

        try:
            fcntl.flock(
                lock_fd,
                fcntl.LOCK_EX,
            )

            if path.exists():
                raise IdentityUpdateRequestConflict(
                    "Une vérification upstream est déjà en attente"
                )

            file_fd = os.open(
                temporary,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL,
                0o640,
            )

            try:
                with os.fdopen(
                    file_fd,
                    "w",
                    encoding="utf-8",
                ) as handle:
                    json.dump(
                        document,
                        handle,
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )

                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())

                os.replace(
                    temporary,
                    path,
                )

                directory_fd = os.open(
                    path.parent,
                    os.O_RDONLY,
                )

                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)

            finally:
                if temporary.exists():
                    temporary.unlink()

        finally:
            os.close(lock_fd)

    except IdentityUpdateRequestConflict:
        raise
    except OSError as exc:
        raise IdentityUpdateRequestError(
            "Impossible d’enregistrer la demande de vérification"
        ) from exc

    return {
        "request_id": request_id,
        "action": "verify_upstream",
        "status": "queued",
        "requested_at": requested_at,
    }
