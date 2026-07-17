from __future__ import annotations

import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.storage import load_json, save_json


_ALLOWED_OBJECT_TYPES = {
    "ou",
    "group",
    "user",
    "computer",
    "contact",
}

_FORBIDDEN_KEYS = {
    "password",
    "temporary_password",
    "secret",
    "token",
    "api_key",
    "credential",
    "credentials",
}

_CACHE_LOCK = threading.RLock()
_CACHE_PATH: str | None = None
_CACHE_MTIME_NS: int | None = None
_CACHE_VALUE: dict[str, Any] | None = None


class ADSnapshotBadRequest(ValueError):
    pass


class ADSnapshotNotFound(LookupError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat().replace("+00:00", "Z")


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None

    text = str(value).strip().replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _normalize_dn(value: Any) -> str:
    return str(value or "").strip()


def _dn_key(value: Any) -> str:
    return _normalize_dn(value).upper()


def _is_dn_inside_base(dn: str, base_dn: str) -> bool:
    normalized_dn = _dn_key(dn)
    normalized_base = _dn_key(base_dn)

    return (
        normalized_dn == normalized_base
        or normalized_dn.endswith("," + normalized_base)
    )


def _check_forbidden_keys(value: Any, path: str = "snapshot") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).strip().lower().replace("-", "_")

            if normalized_key in _FORBIDDEN_KEYS:
                raise ADSnapshotBadRequest(
                    f"Champ sensible interdit dans {path} : {key}"
                )

            _check_forbidden_keys(child, f"{path}.{key}")

    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_forbidden_keys(child, f"{path}[{index}]")


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        clean = value.strip()
        return [clean] if clean else []

    if not isinstance(value, list):
        raise ADSnapshotBadRequest(
            "Les appartenances et les membres doivent être des listes."
        )

    result: list[str] = []

    for item in value:
        clean = str(item or "").strip()

        if clean:
            result.append(clean)

    return result


def _normalize_item(item: Any, base_dn: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ADSnapshotBadRequest(
            "Chaque objet du snapshot doit être un objet JSON."
        )

    normalized = dict(item)

    object_type = str(
        normalized.get("type")
        or normalized.get("object_class")
        or ""
    ).strip().lower()

    if object_type == "organizationalunit":
        object_type = "ou"

    if object_type not in _ALLOWED_OBJECT_TYPES:
        raise ADSnapshotBadRequest(
            f"Type d’objet snapshot non supporté : {object_type or 'vide'}"
        )

    distinguished_name = _normalize_dn(
        normalized.get("distinguished_name")
        or normalized.get("dn")
    )

    if not distinguished_name:
        raise ADSnapshotBadRequest(
            "Un objet du snapshot ne possède aucun DN."
        )

    if not _is_dn_inside_base(distinguished_name, base_dn):
        raise ADSnapshotBadRequest(
            f"Objet hors du périmètre autorisé : {distinguished_name}"
        )

    normalized["type"] = object_type
    normalized["object_class"] = object_type
    normalized["distinguished_name"] = distinguished_name
    normalized["dn"] = distinguished_name

    normalized["members"] = _normalize_string_list(
        normalized.get("members")
    )

    normalized["member_of"] = _normalize_string_list(
        normalized.get("member_of")
    )

    normalized["member_count"] = len(
        normalized["members"]
    )

    return normalized


def _normalize_snapshot(
    payload: Any,
    expected_base_dn: str,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ADSnapshotBadRequest(
            "Le snapshot doit être un objet JSON."
        )

    source = payload.get("snapshot")

    if isinstance(source, dict):
        payload = source

    _check_forbidden_keys(payload)

    base_dn = _normalize_dn(payload.get("base_dn"))

    if not base_dn:
        raise ADSnapshotBadRequest(
            "Le champ base_dn est obligatoire."
        )

    if _dn_key(base_dn) != _dn_key(expected_base_dn):
        raise ADSnapshotBadRequest(
            f"Base DN refusée : {base_dn}"
        )

    raw_items = payload.get("items")

    if not isinstance(raw_items, list):
        raise ADSnapshotBadRequest(
            "Le champ items doit être une liste."
        )

    if len(raw_items) > 10_000:
        raise ADSnapshotBadRequest(
            "Le snapshot dépasse la limite de 10 000 objets."
        )

    deduplicated: dict[str, dict[str, Any]] = {}

    for raw_item in raw_items:
        item = _normalize_item(raw_item, base_dn)
        deduplicated[_dn_key(item["distinguished_name"])] = item

    items = list(deduplicated.values())

    items.sort(
        key=lambda item: (
            str(item.get("type") or ""),
            str(item.get("name") or "").casefold(),
            _dn_key(item.get("distinguished_name")),
        )
    )

    generated_at = str(
        payload.get("generated_at")
        or _utc_now_iso()
    )

    if _parse_datetime(generated_at) is None:
        raise ADSnapshotBadRequest(
            "Le champ generated_at n’est pas une date ISO valide."
        )

    return {
        "version": str(
            payload.get("version")
            or generated_at
        ),
        "generated_at": generated_at,
        "received_at": _utc_now_iso(),
        "domain": str(payload.get("domain") or ""),
        "base_dn": base_dn,
        "controller": str(payload.get("controller") or ""),
        "count": len(items),
        "items": items,
    }


def _path_mtime_ns(path: Path) -> int | None:
    try:
        return path.stat().st_mtime_ns
    except FileNotFoundError:
        return None


def _replace_cache(
    snapshot_file: Path,
    snapshot: dict[str, Any],
) -> None:
    global _CACHE_PATH
    global _CACHE_MTIME_NS
    global _CACHE_VALUE

    with _CACHE_LOCK:
        _CACHE_PATH = str(snapshot_file.resolve())
        _CACHE_MTIME_NS = _path_mtime_ns(snapshot_file)
        _CACHE_VALUE = deepcopy(snapshot)


def receive_ad_snapshot(
    snapshot_file: str | Path,
    payload: Any,
    *,
    expected_base_dn: str,
) -> dict[str, Any]:
    target = Path(snapshot_file)

    snapshot = _normalize_snapshot(
        payload,
        expected_base_dn,
    )

    save_json(target, snapshot)
    _replace_cache(target, snapshot)

    return {
        "success": True,
        "message": "Snapshot Active Directory enregistré.",
        "snapshot": {
            "version": snapshot["version"],
            "generated_at": snapshot["generated_at"],
            "received_at": snapshot["received_at"],
            "controller": snapshot["controller"],
            "base_dn": snapshot["base_dn"],
            "count": snapshot["count"],
        },
    }


def _load_snapshot(
    snapshot_file: Path,
) -> dict[str, Any]:
    global _CACHE_PATH
    global _CACHE_MTIME_NS
    global _CACHE_VALUE

    resolved_path = str(snapshot_file.resolve())
    current_mtime = _path_mtime_ns(snapshot_file)

    with _CACHE_LOCK:
        cache_valid = (
            _CACHE_VALUE is not None
            and _CACHE_PATH == resolved_path
            and _CACHE_MTIME_NS == current_mtime
        )

        if cache_valid:
            return deepcopy(_CACHE_VALUE)

    snapshot = load_json(snapshot_file, {})

    if (
        not isinstance(snapshot, dict)
        or not isinstance(snapshot.get("items"), list)
        or not snapshot.get("generated_at")
    ):
        raise ADSnapshotNotFound(
            "Aucun snapshot Active Directory disponible."
        )

    _replace_cache(snapshot_file, snapshot)

    return deepcopy(snapshot)


def get_ad_snapshot(
    snapshot_file: str | Path,
    *,
    stale_after_seconds: int = 15,
) -> dict[str, Any]:
    target = Path(snapshot_file)
    snapshot = _load_snapshot(target)

    reference_date = (
        _parse_datetime(snapshot.get("received_at"))
        or _parse_datetime(snapshot.get("generated_at"))
    )

    age_seconds: float | None = None

    if reference_date is not None:
        age_seconds = max(
            0.0,
            (_utc_now() - reference_date).total_seconds(),
        )

    snapshot["age_seconds"] = (
        round(age_seconds, 3)
        if age_seconds is not None
        else None
    )

    snapshot["stale_after_seconds"] = stale_after_seconds
    snapshot["is_stale"] = (
        age_seconds is None
        or age_seconds > stale_after_seconds
    )

    return snapshot
