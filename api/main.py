from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from datetime import datetime
from uuid import uuid4
import json
import os

from app.core.config import BASE_DIR, DATA_DIR, TEMPLATES_FILE, REQUESTS_FILE, AUDIT_FILE
from app.core.security import require_api_key
from app.core.storage import load_json, save_json
from app.services.audit import write_audit_log
from app.utils.naming import generate_username, generate_email
from app.models import OnboardingRequest, AgentResult, ResetRequestsPayload, ClaimRequestPayload, ApprovalPayload, DepartmentTemplatePayload, RoleTemplatePayload, OffboardingRequest, ModificationRequest


app = FastAPI(
    title="Enterprise IT Automation Suite",
    description="API MVP pour gérer les arrivées utilisateurs et les demandes Active Directory.",
    version="0.1.0",
    docs_url=None,
    redoc_url=None
)


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

AGENT_STATUS_FILE = DATA_DIR / "agent-status.json"
AGENT_CONFIG_FILE = DATA_DIR / "agent-config.json"



@app.get("/app", include_in_schema=False)
@app.get("/app/{full_path:path}", include_in_schema=False)
def serve_react_app(full_path: str = ""):
    react_index = BASE_DIR / "static" / "app" / "index.html"

    if not react_index.exists():
        raise HTTPException(status_code=404, detail="React build introuvable")

    return FileResponse(react_index)


@app.get("/portal", include_in_schema=False)
@app.get("/portal/{full_path:path}", include_in_schema=False)
def serve_react_portal(full_path: str = ""):
    return serve_react_app(full_path)

@app.get("/docs-local", include_in_schema=False)
def docs_local():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enterprise IT Automation Suite - Docs</title>
        <link rel="stylesheet" type="text/css" href="/static/swagger/swagger-ui.css">
        <style>
            html, body {
                margin: 0;
                padding: 0;
                background: white;
            }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="/static/swagger/swagger-ui-bundle.js"></script>
        <script>
            window.onload = function() {
                SwaggerUIBundle({
                    url: "/openapi.json",
                    dom_id: "#swagger-ui",
                    deepLinking: true,
                    layout: "BaseLayout"
                });
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/")
def root():
    return {
        "name": "Enterprise IT Automation Suite",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/api/templates")
def get_templates():
    return load_json(TEMPLATES_FILE, {"departments": {}})


@app.post("/api/onboarding/request")
def create_onboarding_request(payload: OnboardingRequest, api_key: None = Depends(require_api_key)):
    templates = load_json(TEMPLATES_FILE, {"departments": {}})
    departments = templates.get("departments", {})

    if payload.department not in departments:
        raise HTTPException(status_code=400, detail="Département inconnu")

    department_config = departments[payload.department]
    roles = department_config.get("roles", {})

    if payload.job_title not in roles:
        raise HTTPException(status_code=400, detail="Poste inconnu pour ce département")

    default_groups = department_config.get("default_groups", [])
    role_groups = roles[payload.job_title].get("groups", [])
    manual_groups = payload.manual_groups

    all_groups = sorted(set(default_groups + role_groups + manual_groups))

    request_id = str(uuid4())
    username = generate_username(payload.first_name, payload.last_name)
    email = generate_email(payload.first_name, payload.last_name)

    request_data = {
        "id": request_id,
        "type": "onboarding",
        "status": "waiting_approval",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "input": payload.model_dump(),
        "ad_payload": {
            "first_name": payload.first_name,
            "last_name": payload.last_name,
            "display_name": f"{payload.first_name} {payload.last_name}",
            "username": username,
            "email": email,
            "department": payload.department,
            "job_title": payload.job_title,
            "manager": payload.manager,
            "start_date": payload.start_date,
            "ou": department_config.get("default_ou"),
            "groups": all_groups
        },
        "agent_result": None
    }

    requests = load_json(REQUESTS_FILE, [])
    requests.append(request_data)
    save_json(REQUESTS_FILE, requests)

    write_audit_log(
        action="request_created",
        request_id=request_id,
        actor="api",
        message=f"Demande onboarding créée pour {payload.first_name} {payload.last_name}",
        details={
            "username": username,
            "department": payload.department,
            "job_title": payload.job_title
        }
    )

    return {
        "message": "Demande créée",
        "request": request_data
    }


@app.get("/api/requests")
def list_requests(api_key: None = Depends(require_api_key)):
    return load_json(REQUESTS_FILE, [])


@app.get("/api/requests/{request_id}")
def get_request_by_id(request_id: str, api_key: None = Depends(require_api_key)):
    requests = load_json(REQUESTS_FILE, [])

    for request in requests:
        if request.get("id") == request_id:
            return request

    raise HTTPException(status_code=404, detail="Demande introuvable")




def get_default_agent_config():
    return {
        "interval_minutes": 2,
        "allowed_intervals": [1, 2, 5, 10, 15, 30],
        "task_name": "EITAS Employee Lifecycle Agent",
        "message": "Configuration agent par défaut"
    }


@app.get("/api/agent/config")
def get_agent_config(api_key: None = Depends(require_api_key)):
    config = get_default_agent_config()

    if AGENT_CONFIG_FILE.exists():
        try:
            saved = json.loads(AGENT_CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                config.update(saved)
        except Exception:
            raise HTTPException(status_code=500, detail="Impossible de lire la configuration agent")

    if config.get("interval_minutes") not in config["allowed_intervals"]:
        config["interval_minutes"] = 2

    return config


@app.post("/api/agent/config")
def update_agent_config(payload: dict, api_key: None = Depends(require_api_key)):
    config = get_default_agent_config()

    try:
        interval_minutes = int(payload.get("interval_minutes"))
    except Exception:
        raise HTTPException(status_code=400, detail="interval_minutes invalide")

    if interval_minutes not in config["allowed_intervals"]:
        raise HTTPException(
            status_code=400,
            detail=f"Fréquence non autorisée. Valeurs possibles : {config['allowed_intervals']}"
        )

    config["interval_minutes"] = interval_minutes
    config["message"] = f"Fréquence agent configurée à {interval_minutes} minute(s)"
    config["updated_at"] = datetime.utcnow().isoformat() + "Z"

    save_json(AGENT_CONFIG_FILE, config)

    return {
        "ok": True,
        "message": "Configuration agent enregistrée",
        "config": config
    }


@app.post("/api/agent/heartbeat")
def receive_agent_heartbeat(payload: dict, api_key: None = Depends(require_api_key)):
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
        "task": payload.get("task") or {}
    }

    save_json(AGENT_STATUS_FILE, status)

    return {
        "ok": True,
        "message": "Heartbeat agent enregistré",
        "status": status
    }


@app.get("/api/agent/status")
def get_agent_status(api_key: None = Depends(require_api_key)):
    if not AGENT_STATUS_FILE.exists():
        return {
            "online": False,
            "message": "Aucun heartbeat agent reçu",
            "received_at": None,
            "seconds_since_seen": None
        }

    try:
        status = json.loads(AGENT_STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="Impossible de lire le statut agent")

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


@app.get("/api/agent/pending")
def get_pending_requests(api_key: None = Depends(require_api_key)):
    requests = load_json(REQUESTS_FILE, [])

    pending = [
        request for request in requests
        if request.get("status") == "pending"
    ]

    return {
        "count": len(pending),
        "requests": pending
    }


@app.post("/api/agent/claim/{request_id}")
def claim_request(request_id: str, payload: ClaimRequestPayload, api_key: None = Depends(require_api_key)):
    requests = load_json(REQUESTS_FILE, [])

    for request in requests:
        if request.get("id") == request_id:
            current_status = request.get("status")

            if current_status != "pending":
                raise HTTPException(
                    status_code=409,
                    detail=f"Demande non disponible. Statut actuel : {current_status}"
                )

            request["status"] = "processing"
            request["processing_at"] = datetime.utcnow().isoformat() + "Z"
            request["processing_by"] = payload.agent_name or "unknown-agent"

            save_json(REQUESTS_FILE, requests)

            write_audit_log(
                action="request_claimed",
                request_id=request_id,
                actor=payload.agent_name or "unknown-agent",
                message="Demande prise en charge par un agent",
                details={
                    "status": "processing"
                }
            )

            return {
                "message": "Demande prise en charge",
                "request_id": request_id,
                "status": "processing",
                "request": request
            }

    raise HTTPException(status_code=404, detail="Demande introuvable")


@app.post("/api/agent/result/{request_id}")
def submit_agent_result(request_id: str, result: AgentResult, api_key: None = Depends(require_api_key)):
    requests = load_json(REQUESTS_FILE, [])
    found = False

    for request in requests:
        if request.get("id") == request_id:
            found = True
            request["status"] = "completed" if result.success else "failed"
            request["completed_at"] = datetime.utcnow().isoformat() + "Z"
            request["agent_result"] = result.model_dump()
            break

    if not found:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    save_json(REQUESTS_FILE, requests)

    write_audit_log(
        action="request_completed" if result.success else "request_failed",
        request_id=request_id,
        actor=result.details.get("server", "agent") if isinstance(result.details, dict) else "agent",
        message=result.message,
        details=result.details
    )

    return {
        "message": "Résultat agent enregistré",
        "request_id": request_id
    }


@app.post("/api/admin/requests/reset")
def reset_requests(payload: ResetRequestsPayload, api_key: None = Depends(require_api_key)):
    if payload.confirm != "RESET":
        raise HTTPException(
            status_code=400,
            detail="Confirmation invalide. Utilise exactement RESET."
        )

    requests = load_json(REQUESTS_FILE, [])
    deleted_count = len(requests)
    backup_file = None

    if deleted_count > 0:
        backup_file = DATA_DIR / f"requests.backup.{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
        save_json(backup_file, requests)

    save_json(REQUESTS_FILE, [])

    write_audit_log(
        action="requests_reset",
        actor="admin",
        message="Réinitialisation des demandes",
        details={
            "deleted_count": deleted_count,
            "backup_file": backup_file.name if backup_file else None
        }
    )

    return {
        "message": "Demandes réinitialisées",
        "deleted_count": deleted_count,
        "backup_file": backup_file.name if backup_file else None
    }


@app.post("/api/admin/requests/{request_id}/retry")
def retry_request(request_id: str, api_key: None = Depends(require_api_key)):
    requests = load_json(REQUESTS_FILE, [])
    found = False

    for request in requests:
        if request.get("id") == request_id:
            found = True
            request["status"] = "pending"
            request["retried_at"] = datetime.utcnow().isoformat() + "Z"
            request["completed_at"] = None
            request["agent_result"] = None
            break

    if not found:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    save_json(REQUESTS_FILE, requests)

    write_audit_log(
        action="request_retried",
        request_id=request_id,
        actor="admin",
        message="Demande remise en attente",
        details={
            "status": "pending"
        }
    )

    return {
        "message": "Demande remise en attente",
        "request_id": request_id,
        "status": "pending"
    }


@app.post("/api/admin/requests/{request_id}/approve")
def approve_request(request_id: str, payload: ApprovalPayload, api_key: None = Depends(require_api_key)):
    requests = load_json(REQUESTS_FILE, [])

    for request in requests:
        if request.get("id") == request_id:
            current_status = request.get("status")

            if current_status != "waiting_approval":
                raise HTTPException(
                    status_code=409,
                    detail=f"Demande non validable. Statut actuel : {current_status}"
                )

            request["status"] = "pending"
            request["approved"] = True
            request["approved_by"] = payload.approved_by
            request["approved_at"] = datetime.utcnow().isoformat() + "Z"
            request["approval_comment"] = payload.comment

            save_json(REQUESTS_FILE, requests)

            write_audit_log(
                action="request_approved",
                request_id=request_id,
                actor=payload.approved_by,
                message="Demande validée",
                details={
                    "comment": payload.comment,
                    "status": "pending"
                }
            )

            return {
                "message": "Demande validée",
                "request_id": request_id,
                "status": "pending"
            }

    raise HTTPException(status_code=404, detail="Demande introuvable")


@app.post("/api/admin/requests/{request_id}/reject")
def reject_request(request_id: str, payload: ApprovalPayload, api_key: None = Depends(require_api_key)):
    requests = load_json(REQUESTS_FILE, [])

    for request in requests:
        if request.get("id") == request_id:
            current_status = request.get("status")

            if current_status not in ["waiting_approval", "pending"]:
                raise HTTPException(
                    status_code=409,
                    detail=f"Demande non rejetable. Statut actuel : {current_status}"
                )

            request["status"] = "rejected"
            request["approved"] = False
            request["rejected_by"] = payload.approved_by
            request["rejected_at"] = datetime.utcnow().isoformat() + "Z"
            request["rejection_comment"] = payload.comment

            save_json(REQUESTS_FILE, requests)

            write_audit_log(
                action="request_rejected",
                request_id=request_id,
                actor=payload.approved_by,
                message="Demande rejetée",
                details={
                    "comment": payload.comment,
                    "status": "rejected"
                }
            )

            return {
                "message": "Demande rejetée",
                "request_id": request_id,
                "status": "rejected"
            }

    raise HTTPException(status_code=404, detail="Demande introuvable")


@app.get("/api/audit-logs")
def list_audit_logs(limit: int = 50, api_key: None = Depends(require_api_key)):
    if not AUDIT_FILE.exists():
        return {
            "count": 0,
            "logs": []
        }

    lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines()
    selected_lines = lines[-limit:]

    logs = []
    for line in selected_lines:
        try:
            logs.append(json.loads(line))
        except json.JSONDecodeError:
            logs.append({
                "error": "invalid_log_line",
                "raw": line
            })

    return {
        "count": len(logs),
        "logs": logs
    }


@app.get("/api/admin/templates")
def admin_get_templates(api_key: None = Depends(require_api_key)):
    return load_json(TEMPLATES_FILE, {"departments": {}})


@app.post("/api/admin/templates/departments")
def upsert_department_template(payload: DepartmentTemplatePayload, api_key: None = Depends(require_api_key)):
    templates = load_json(TEMPLATES_FILE, {"departments": {}})
    departments = templates.setdefault("departments", {})

    existing_department = departments.get(payload.name, {})
    existing_roles = existing_department.get("roles", {})

    departments[payload.name] = {
        "default_ou": payload.default_ou,
        "default_groups": sorted(set(payload.default_groups)),
        "roles": existing_roles
    }

    save_json(TEMPLATES_FILE, templates)

    write_audit_log(
        action="template_department_upserted",
        actor="admin",
        message=f"Département template créé/modifié : {payload.name}",
        details={
            "department": payload.name,
            "default_ou": payload.default_ou,
            "default_groups": payload.default_groups
        }
    )

    return {
        "message": "Département template créé/modifié",
        "department": departments[payload.name]
    }


@app.delete("/api/admin/templates/departments/{department_name}")
def delete_department_template(department_name: str, api_key: None = Depends(require_api_key)):
    templates = load_json(TEMPLATES_FILE, {"departments": {}})
    departments = templates.setdefault("departments", {})

    if department_name not in departments:
        raise HTTPException(status_code=404, detail="Département template introuvable")

    deleted_department = departments.pop(department_name)

    save_json(TEMPLATES_FILE, templates)

    write_audit_log(
        action="template_department_deleted",
        actor="admin",
        message=f"Département template supprimé : {department_name}",
        details={
            "department": department_name
        }
    )

    return {
        "message": "Département template supprimé",
        "department_name": department_name,
        "deleted": deleted_department
    }


@app.post("/api/admin/templates/departments/{department_name}/roles")
def upsert_role_template(department_name: str, payload: RoleTemplatePayload, api_key: None = Depends(require_api_key)):
    templates = load_json(TEMPLATES_FILE, {"departments": {}})
    departments = templates.setdefault("departments", {})

    if department_name not in departments:
        raise HTTPException(status_code=404, detail="Département template introuvable")

    roles = departments[department_name].setdefault("roles", {})

    roles[payload.name] = {
        "groups": sorted(set(payload.groups))
    }

    save_json(TEMPLATES_FILE, templates)

    write_audit_log(
        action="template_role_upserted",
        actor="admin",
        message=f"Poste template créé/modifié : {payload.name}",
        details={
            "department": department_name,
            "role": payload.name,
            "groups": payload.groups
        }
    )

    return {
        "message": "Poste template créé/modifié",
        "department": department_name,
        "role": payload.name,
        "data": roles[payload.name]
    }


@app.delete("/api/admin/templates/departments/{department_name}/roles/{role_name}")
def delete_role_template(department_name: str, role_name: str, api_key: None = Depends(require_api_key)):
    templates = load_json(TEMPLATES_FILE, {"departments": {}})
    departments = templates.setdefault("departments", {})

    if department_name not in departments:
        raise HTTPException(status_code=404, detail="Département template introuvable")

    roles = departments[department_name].setdefault("roles", {})

    if role_name not in roles:
        raise HTTPException(status_code=404, detail="Poste template introuvable")

    deleted_role = roles.pop(role_name)

    save_json(TEMPLATES_FILE, templates)

    write_audit_log(
        action="template_role_deleted",
        actor="admin",
        message=f"Poste template supprimé : {role_name}",
        details={
            "department": department_name,
            "role": role_name
        }
    )

    return {
        "message": "Poste template supprimé",
        "department": department_name,
        "role": role_name,
        "deleted": deleted_role
    }


@app.post("/api/offboarding/request")
def create_offboarding_request(payload: OffboardingRequest, api_key: None = Depends(require_api_key)):
    requests = load_json(REQUESTS_FILE, [])

    request_id = str(uuid4())
    now = datetime.utcnow().isoformat() + "Z"

    offboarding_payload = {
        "username": payload.username,
        "display_name": payload.display_name,
        "department": payload.department,
        "manager": payload.manager,
        "end_date": payload.end_date,
        "disable_account": payload.disable_account,
        "remove_groups": payload.remove_groups,
        "move_to_ou": payload.move_to_ou,
        "convert_mailbox": payload.convert_mailbox,
        "forward_to": payload.forward_to,
        "comment": payload.comment
    }

    request = {
        "id": request_id,
        "type": "offboarding",
        "status": "waiting_approval",
        "created_at": now,
        "approved": False,
        "approved_by": None,
        "approved_at": None,
        "rejected_by": None,
        "rejected_at": None,
        "processing_by": None,
        "processing_at": None,
        "completed_at": None,
        "failed_at": None,
        "payload": payload.dict(),
        "ad_payload": offboarding_payload,
        "agent_result": None
    }

    requests.append(request)
    save_json(REQUESTS_FILE, requests)

    write_audit_log(
        action="offboarding_request_created",
        request_id=request_id,
        actor="api",
        message=f"Demande offboarding créée pour {payload.display_name}",
        details={
            "username": payload.username,
            "display_name": payload.display_name,
            "department": payload.department,
            "end_date": payload.end_date
        }
    )

    return {
        "message": "Demande offboarding créée",
        "request": request
    }


@app.post("/api/modification/request")
def create_modification_request(payload: ModificationRequest, api_key: None = Depends(require_api_key)):
    requests = load_json(REQUESTS_FILE, [])

    request_id = str(uuid4())
    now = datetime.utcnow().isoformat() + "Z"

    modification_payload = {
        "username": payload.username,
        "display_name": payload.display_name,
        "department": payload.new_department or payload.current_department,
        "job_title": payload.new_job_title or payload.current_job_title,
        "current_department": payload.current_department,
        "current_job_title": payload.current_job_title,
        "new_department": payload.new_department,
        "new_job_title": payload.new_job_title,
        "manager": payload.manager,
        "effective_date": payload.effective_date,
        "add_groups": payload.add_groups,
        "remove_groups": payload.remove_groups,
        "move_to_ou": payload.move_to_ou,
        "comment": payload.comment
    }

    request = {
        "id": request_id,
        "type": "modification",
        "status": "waiting_approval",
        "created_at": now,
        "approved": False,
        "approved_by": None,
        "approved_at": None,
        "rejected_by": None,
        "rejected_at": None,
        "processing_by": None,
        "processing_at": None,
        "completed_at": None,
        "failed_at": None,
        "payload": modification_payload,
        "ad_payload": modification_payload,
        "agent_result": None
    }

    requests.append(request)
    save_json(REQUESTS_FILE, requests)

    write_audit_log(
        action="modification_request_created",
        request_id=request_id,
        actor="api",
        message=f"Demande modification créée pour {payload.display_name}",
        details={
            "username": payload.username,
            "display_name": payload.display_name,
            "current_department": payload.current_department,
            "current_job_title": payload.current_job_title,
            "new_department": payload.new_department,
            "new_job_title": payload.new_job_title,
            "add_groups": payload.add_groups,
            "remove_groups": payload.remove_groups
        }
    )

    return {
        "message": "Demande modification créée",
        "request": request
    }
