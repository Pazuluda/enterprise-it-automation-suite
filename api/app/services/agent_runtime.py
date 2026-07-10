from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.storage import load_json, save_json


class AgentRuntimeError(Exception):
    pass


class AgentRuntimeBadRequest(AgentRuntimeError):
    pass


class AgentRuntimeNotFound(AgentRuntimeError):
    pass


class AgentRuntimeConflict(AgentRuntimeError):
    pass


class AgentRuntimeStorageError(AgentRuntimeError):
    pass


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def get_default_agent_config() -> dict:
    return {
        "interval_minutes": 2,
        "allowed_intervals": [1, 2, 5, 10, 15, 30],
        "task_name": "EITAS Employee Lifecycle Agent",
        "pause_processing": False,
        "message": "Configuration agent par défaut",
    }


def get_agent_config(config_file: Path) -> dict:
    config = get_default_agent_config()

    if config_file.exists():
        try:
            saved = load_json(config_file, {})
            if isinstance(saved, dict):
                config.update(saved)
        except Exception as exc:
            raise AgentRuntimeStorageError("Impossible de lire la configuration agent") from exc

    if config.get("interval_minutes") not in config["allowed_intervals"]:
        config["interval_minutes"] = 2

    return config


def update_agent_config(config_file: Path, payload: dict) -> tuple[dict, dict | None]:
    config = get_default_agent_config()

    try:
        interval_minutes = int(payload.get("interval_minutes"))
    except Exception as exc:
        raise AgentRuntimeBadRequest("interval_minutes invalide") from exc

    if interval_minutes not in config["allowed_intervals"]:
        raise AgentRuntimeBadRequest(
            f"Fréquence non autorisée. Valeurs possibles : {config['allowed_intervals']}"
        )

    config["interval_minutes"] = interval_minutes

    if "pause_processing" in payload:
        config["pause_processing"] = bool(payload.get("pause_processing"))

    if config.get("pause_processing"):
        config["message"] = f"Agent en pause. Fréquence conservée à {interval_minutes} minute(s)"
    else:
        config["message"] = f"Fréquence agent configurée à {interval_minutes} minute(s)"

    config["updated_at"] = utc_now_iso()

    previous_config = get_agent_config(config_file)

    save_json(config_file, config)

    changed_fields = {}

    if previous_config.get("interval_minutes") != config.get("interval_minutes"):
        changed_fields["interval_minutes"] = {
            "old": previous_config.get("interval_minutes"),
            "new": config.get("interval_minutes"),
        }

    if previous_config.get("pause_processing") != config.get("pause_processing"):
        changed_fields["pause_processing"] = {
            "old": previous_config.get("pause_processing"),
            "new": config.get("pause_processing"),
        }

    audit_event = None

    if changed_fields:
        if "pause_processing" in changed_fields:
            action = "agent_processing_paused" if config.get("pause_processing") else "agent_processing_resumed"
            message = "Traitement agent mis en pause" if config.get("pause_processing") else "Traitement agent repris"
        else:
            action = "agent_interval_updated"
            message = f"Fréquence agent mise à jour : {config.get('interval_minutes')} minute(s)"

        audit_event = {
            "action": action,
            "request_id": None,
            "actor": "react-admin",
            "message": message,
            "details": {
                "changed_fields": changed_fields,
                "interval_minutes": config.get("interval_minutes"),
                "pause_processing": config.get("pause_processing"),
                "task_name": config.get("task_name"),
            },
        }

    return {
        "ok": True,
        "message": "Configuration agent enregistrée",
        "config": config,
    }, audit_event


def receive_agent_heartbeat(status_file: Path, payload: dict) -> dict:
    now = datetime.utcnow()

    status = {
        "online": True,
        "agent_name": payload.get("agent_name") or payload.get("agent") or "unknown",
        "computer_name": payload.get("computer_name") or "",
        "mode": payload.get("mode") or "unknown",
        "script": payload.get("script") or "",
        "status": payload.get("status") or "running",
        "message": payload.get("message") or "Heartbeat reçu",
        "received_at": now.isoformat() + "Z",
        "api_base_url": payload.get("api_base_url") or "",
        "version": payload.get("version") or "0.1.0",
        "schedule_interval_minutes": payload.get("schedule_interval_minutes"),
        "pause_processing": bool(payload.get("pause_processing")),
        "task": payload.get("task") or {},
    }

    save_json(status_file, status)

    return {
        "ok": True,
        "message": "Heartbeat agent enregistré",
        "status": status,
    }


def get_agent_status(status_file: Path) -> dict:
    if not status_file.exists():
        return {
            "online": False,
            "message": "Aucun heartbeat agent reçu",
            "received_at": None,
            "seconds_since_seen": None,
        }

    try:
        status = load_json(status_file, {})
    except Exception as exc:
        raise AgentRuntimeStorageError("Impossible de lire le statut agent") from exc

    received_at_raw = status.get("received_at")
    seconds_since_seen = None
    online = False

    if received_at_raw:
        try:
            received_at = datetime.fromisoformat(str(received_at_raw).replace("Z", ""))
            seconds_since_seen = int((datetime.utcnow() - received_at).total_seconds())
            online = seconds_since_seen <= 300
        except Exception:
            seconds_since_seen = None
            online = False

    status["online"] = online
    status["seconds_since_seen"] = seconds_since_seen

    if online:
        status["message"] = status.get("message") or "Agent actif"
    else:
        status["message"] = "Agent non vu depuis plus de 5 minutes"

    return status


def get_pending_requests(requests_file: Path) -> dict:
    requests = load_json(requests_file, [])

    pending = [
        request for request in requests
        if request.get("status") == "pending"
    ]

    return {
        "count": len(pending),
        "requests": pending,
    }


def claim_request(requests_file: Path, request_id: str, agent_name: str | None) -> tuple[dict, dict]:
    requests = load_json(requests_file, [])
    actor = agent_name or "unknown-agent"

    for request in requests:
        if request.get("id") == request_id:
            current_status = request.get("status")

            if current_status != "pending":
                raise AgentRuntimeConflict(
                    f"Demande non disponible. Statut actuel : {current_status}"
                )

            request["status"] = "processing"
            request["processing_at"] = utc_now_iso()
            request["processing_by"] = actor

            save_json(requests_file, requests)

            audit_event = {
                "action": "request_claimed",
                "request_id": request_id,
                "actor": actor,
                "message": "Demande prise en charge par un agent",
                "details": {
                    "status": "processing",
                },
            }

            return {
                "message": "Demande prise en charge",
                "request_id": request_id,
                "status": "processing",
                "request": request,
            }, audit_event

    raise AgentRuntimeNotFound("Demande introuvable")


def submit_agent_result(requests_file: Path, request_id: str, result: dict) -> tuple[dict, dict]:
    requests = load_json(requests_file, [])
    found = False

    success = bool(result.get("success"))
    message = result.get("message") or ""
    details = result.get("details") or {}

    for request in requests:
        if request.get("id") == request_id:
            found = True
            request["status"] = "completed" if success else "failed"
            request["completed_at"] = utc_now_iso()
            request["agent_result"] = result
            break

    if not found:
        raise AgentRuntimeNotFound("Demande introuvable")

    save_json(requests_file, requests)

    actor = details.get("server", "agent") if isinstance(details, dict) else "agent"

    audit_event = {
        "action": "request_completed" if success else "request_failed",
        "request_id": request_id,
        "actor": actor,
        "message": message,
        "details": details,
    }

    return {
        "message": "Résultat agent enregistré",
        "request_id": request_id,
    }, audit_event
