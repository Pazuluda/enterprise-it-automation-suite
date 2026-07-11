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



def _is_jobs_list_path(path: Path) -> bool:
    return path.name.endswith("-jobs.json")


def _job_status_rank(job: dict[str, Any]) -> int:
    status = str(job.get("status") or "").lower()

    return {
        "created": 0,
        "pending": 1,
        "processing": 2,
        "completed": 3,
        "failed": 3,
    }.get(status, 0)


def _job_timestamp(job: dict[str, Any]) -> str:
    return str(
        job.get("completed_at")
        or job.get("claimed_at")
        or job.get("created_at")
        or ""
    )


def _pick_newer_job(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    existing_rank = _job_status_rank(existing)
    incoming_rank = _job_status_rank(incoming)

    if incoming_rank > existing_rank:
        return incoming

    if incoming_rank < existing_rank:
        return existing

    if _job_timestamp(incoming) >= _job_timestamp(existing):
        return incoming

    return existing


def _merge_job_lists(existing: Any, incoming: Any) -> Any:
    if not isinstance(existing, list) or not isinstance(incoming, list):
        return incoming

    merged: dict[str, dict[str, Any]] = {}
    passthrough: list[Any] = []

    for item in existing:
        if isinstance(item, dict) and item.get("id"):
            merged[item["id"]] = item
        else:
            passthrough.append(item)

    for item in incoming:
        if isinstance(item, dict) and item.get("id"):
            job_id = item["id"]
            if job_id in merged:
                merged[job_id] = _pick_newer_job(merged[job_id], item)
            else:
                merged[job_id] = item
        else:
            passthrough.append(item)

    return passthrough + list(merged.values())

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

        if _is_jobs_list_path(target) and isinstance(data, list) and target.exists():
            try:
                existing_raw = target.read_text(encoding="utf-8-sig", errors="replace")
                existing_data = json.loads(existing_raw) if existing_raw.strip() else []
                data = _merge_job_lists(existing_data, data)
            except json.JSONDecodeError:
                data = _merge_job_lists(_recover_json_values(existing_raw, []), data)

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
