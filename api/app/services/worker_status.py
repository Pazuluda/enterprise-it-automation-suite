from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4


class WorkerStatusBadRequest(ValueError):
    pass


ERROR_STATUSES = {"error", "failed", "stopped", "dead"}


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


def _append_jsonl(path, item):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")


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
    is_error = status in ERROR_STATUSES

    decorated = dict(record)
    decorated["age_seconds"] = age_seconds
    decorated["stale_after_seconds"] = stale_after
    decorated["is_stale"] = is_stale
    decorated["is_error"] = is_error
    decorated["healthy"] = (not is_stale) and (not is_error)

    return decorated


def _health_state(worker):
    status = _text(worker.get("status"), "unknown").lower()

    if status in ERROR_STATUSES:
        return "error"

    if worker.get("is_stale"):
        return "stale"

    if worker.get("healthy"):
        return "healthy"

    return "unknown"


def _state_label(state):
    return {
        "healthy": "OK",
        "stale": "Silencieux",
        "error": "Erreur",
        "unknown": "Inconnu",
    }.get(state, state)


def _event_message(worker, previous_state, current_state):
    name = worker.get("worker_name") or worker.get("worker_id") or "Worker"

    if previous_state == "healthy" and current_state == "stale":
        return f"{name} ne répond plus."

    if previous_state == "stale" and current_state == "healthy":
        return f"{name} est revenu en ligne."

    if current_state == "error":
        return f"{name} signale une erreur."

    if current_state == "healthy":
        return f"{name} est sain."

    return f"{name} est passé de {_state_label(previous_state)} à {_state_label(current_state)}."


def _write_event(events_path, worker, previous_state, current_state):
    if not events_path:
        return

    if not previous_state:
        previous_state = "unknown"

    if previous_state == current_state:
        return

    _append_jsonl(events_path, {
        "id": str(uuid4()),
        "created_at": _now_iso(),
        "worker_id": worker.get("worker_id", ""),
        "worker_name": worker.get("worker_name", worker.get("worker_id", "")),
        "agent_name": worker.get("agent_name", ""),
        "role": worker.get("role", ""),
        "mode": worker.get("mode", ""),
        "previous_state": previous_state,
        "current_state": current_state,
        "previous_state_label": _state_label(previous_state),
        "current_state_label": _state_label(current_state),
        "status": worker.get("status", ""),
        "age_seconds": worker.get("age_seconds"),
        "stale_after_seconds": worker.get("stale_after_seconds"),
        "message": _event_message(worker, previous_state, current_state),
        "details": worker.get("details") if isinstance(worker.get("details"), dict) else {},
    })


def receive_worker_heartbeat(path, payload, events_path=None):
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

    previous_record = data["workers"].get(worker_id)
    previous_state = "unknown"

    if isinstance(previous_record, dict):
        previous_decorated = _decorate_worker(previous_record)
        previous_state = _text(previous_record.get("health_state"), _health_state(previous_decorated))

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

    decorated = _decorate_worker(record)
    current_state = _health_state(decorated)

    record["health_state"] = current_state
    record["health_state_updated_at"] = now
    decorated["health_state"] = current_state
    decorated["health_state_updated_at"] = now

    _write_event(events_path, decorated, previous_state, current_state)

    data["workers"][worker_id] = record
    data["updated_at"] = now

    _save_json(path, data)

    return {
        "success": True,
        "worker": decorated,
    }


def get_worker_status(path, events_path=None):
    now = _now()
    data = _load_json(path)

    workers = []
    changed = False

    for worker_id, record in data.get("workers", {}).items():
        if not isinstance(record, dict):
            continue

        decorated = _decorate_worker(record, now=now)
        previous_state = _text(record.get("health_state"), _health_state(decorated))
        current_state = _health_state(decorated)

        if previous_state != current_state:
            _write_event(events_path, decorated, previous_state, current_state)
            record["health_state"] = current_state
            record["health_state_updated_at"] = _now_iso()
            decorated["health_state"] = current_state
            decorated["health_state_updated_at"] = record["health_state_updated_at"]
            changed = True

        workers.append(decorated)

    if changed:
        data["updated_at"] = _now_iso()
        _save_json(path, data)

    workers.sort(key=lambda item: (item.get("agent_name", ""), item.get("worker_name", "")))

    healthy = sum(1 for item in workers if item.get("healthy"))
    stale = sum(1 for item in workers if item.get("is_stale"))
    errors = sum(1 for item in workers if str(item.get("status", "")).lower() in ERROR_STATUSES)

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


def get_worker_events(path, limit=100):
    path = Path(path)
    limit = max(1, min(_int(limit, 100), 500))

    if not path.exists():
        return {
            "events": [],
            "total_returned": 0,
            "limit": limit,
        }

    events = []

    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if isinstance(item, dict):
                    events.append(item)
    except OSError:
        events = []

    events = events[-limit:]
    events.reverse()

    return {
        "events": events,
        "total_returned": len(events),
        "limit": limit,
    }
