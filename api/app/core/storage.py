from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any


_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, threading.RLock] = {}


def _path_key(path: Path) -> str:
    return str(path.resolve())


def _get_path_lock(path: Path) -> threading.RLock:
    key = _path_key(path)

    with _LOCKS_GUARD:
        if key not in _PATH_LOCKS:
            _PATH_LOCKS[key] = threading.RLock()

        return _PATH_LOCKS[key]


def _recover_json_values(raw: str, default: Any) -> Any:
    decoder = json.JSONDecoder()
    idx = 0
    values = []

    while idx < len(raw):
        while idx < len(raw) and raw[idx].isspace():
            idx += 1

        if idx >= len(raw):
            break

        value, end = decoder.raw_decode(raw, idx)
        values.append(value)
        idx = end

    if not values:
        return default

    if isinstance(default, list):
        items = []

        for value in values:
            if isinstance(value, list):
                items.extend(value)
            elif isinstance(value, dict):
                if isinstance(value.get("jobs"), list):
                    items.extend(value["jobs"])
                elif value.get("id"):
                    items.append(value)

        deduped = {}
        without_id = []

        for item in items:
            if isinstance(item, dict) and item.get("id"):
                deduped[item["id"]] = item
            else:
                without_id.append(item)

        return without_id + list(deduped.values())

    if isinstance(default, dict):
        merged = {}

        for value in values:
            if isinstance(value, dict):
                merged.update(value)

        return merged or values[-1]

    return values[-1]


def load_json(path: str | Path, default: Any) -> Any:
    target = Path(path)

    if not target.exists():
        return default

    lock = _get_path_lock(target)

    with lock:
        raw = target.read_text(encoding="utf-8-sig", errors="replace")

        if not raw.strip():
            return default

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            if "Extra data" not in str(exc):
                raise

            recovered = _recover_json_values(raw, default)
            save_json(target, recovered)
            return recovered


def save_json(path: str | Path, data: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    lock = _get_path_lock(target)

    with lock:
        tmp = target.with_name(
            f".{target.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )

        payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp, target)

        try:
            dir_fd = os.open(str(target.parent), os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
