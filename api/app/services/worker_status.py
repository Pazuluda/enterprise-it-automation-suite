from datetime import datetime, timezone
import json
from pathlib import Path


class WorkerStatusBadRequest(ValueError):
    pass


def _now():
    return datetime.now(timezone.utc)


def _now_iso():
    return _now().isoformat()


def _load_json(path):
    path = Path(path)

    if not path.exists():
        return {"workers": {}}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return {"workers": {}}

    if not isinstance(data, dict):
        return {"workers": {}}

    if not isinstance(data.get("workers"), dict):
        data["workers"] = {}

    return data


def _save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(path.suffix + ".tmp")

    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    tmp.replace(path)


def _text(value, default=""):
    if value is None:
        return default

    value = str(value).strip()

    if not value:
        return default

    return value


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_dt(value):
    if not value:
        return None

    try:
        normalized = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _decorate_worker(record, now=None):
    if now is None:
        now = _now()

    last_seen = _parse_dt(record.get("last_seen_at"))
    stale_after = _int(record.get("stale_after_seconds"), 120)

    if stale_after <= 0:
        stale_after = 120

    age_seconds = None
    if last_seen:
        age_seconds = int((now - last_seen).total_seconds())

    status = _text(record.get("status"), "unknown").lower()

    is_stale = age_seconds is None or age_seconds > stale_after
    is_error = status in {"error", "failed", "stopped", "dead"}

    decorated = dict(record)
    decorated["age_seconds"] = age_seconds
    decorated["stale_after_seconds"] = stale_after
    decorated["is_stale"] = is_stale
    decorated["healthy"] = (not is_stale) and (not is_error)

    return decorated


def receive_worker_heartbeat(path, payload):
    if not isinstance(payload, dict):
        raise WorkerStatusBadRequest("Payload heartbeat worker invalide")

    worker_id = _text(
        payload.get("worker_id")
        or payload.get("worker_name")
        or payload.get("name")
    )

    if not worker_id:
        raise WorkerStatusBadRequest("worker_id ou worker_name manquant")

    agent_name = _text(
        payload.get("agent_name")
        or payload.get("agent")
        or payload.get("hostname"),
        "unknown-agent",
    )

    now = _now_iso()
    data = _load_json(path)

    record = {
        "worker_id": worker_id,
        "worker_name": _text(payload.get("worker_name"), worker_id),
        "agent_name": agent_name,
        "role": _text(payload.get("role"), worker_id),
        "status": _text(payload.get("status"), "running"),
        "mode": _text(payload.get("mode"), ""),
        "pid": _int(payload.get("pid"), 0),
        "version": _text(payload.get("version"), ""),
        "details": payload.get("details") if isinstance(payload.get("details"), dict) else {},
        "last_seen_at": now,
        "stale_after_seconds": _int(payload.get("stale_after_seconds"), 120),
    }

    data["workers"][worker_id] = record
    data["updated_at"] = now

    _save_json(path, data)

    return {
        "success": True,
        "worker": _decorate_worker(record),
    }


def get_worker_status(path):
    now = _now()
    data = _load_json(path)

    workers = []
    for record in data.get("workers", {}).values():
        if isinstance(record, dict):
            workers.append(_decorate_worker(record, now=now))

    workers.sort(key=lambda item: (item.get("agent_name", ""), item.get("worker_name", "")))

    healthy = sum(1 for item in workers if item.get("healthy"))
    stale = sum(1 for item in workers if item.get("is_stale"))
    errors = sum(1 for item in workers if str(item.get("status", "")).lower() in {"error", "failed", "stopped", "dead"})

    return {
        "updated_at": _now_iso(),
        "summary": {
            "total": len(workers),
            "healthy": healthy,
            "stale": stale,
            "errors": errors,
        },
        "workers": workers,
    }
