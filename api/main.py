from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from datetime import datetime
import json
import os

from app.core.config import BASE_DIR, DATA_DIR, TEMPLATES_FILE, REQUESTS_FILE, AUDIT_FILE
from app.core.security import (
    require_api_key,
    require_roles,
    require_roles_or_api_key,
)

from app.core.identity_update_security import (
    require_identity_update_roles,
)
from app.core.storage import load_json, save_json
from app.services.audit import write_audit_log
from app.services.identity_update import (
    IdentityUpdateRequestConflict,
    IdentityUpdateRequestError,
    IdentityUpdateStatusUnavailable,
    create_identity_update_source_check_request as
    service_create_identity_update_source_check_request,
    get_identity_update_status as
    service_get_identity_update_status,
)
from app.services.requests import (
    RequestNotFound,
    get_request_by_id as service_get_request_by_id,
    list_requests as service_list_requests,
)
from app.services.templates import (
    TemplatesNotFound,
    delete_department_template as service_delete_department_template,
    delete_role_template as service_delete_role_template,
    get_templates as service_get_templates,
    upsert_department_template as service_upsert_department_template,
    upsert_role_template as service_upsert_role_template,
)
from app.services.employee_lifecycle import (
    EmployeeLifecycleBadRequest,
    create_modification_request as service_create_modification_request,
    create_offboarding_request as service_create_offboarding_request,
    create_onboarding_request as service_create_onboarding_request,
)

from app.services.ad_jobs import (
    ADJobsBadRequest,
    ADJobsConflict,
    ADJobsNotFound,
    claim_ad_check_job as service_claim_ad_check_job,
    claim_ad_lookup_job as service_claim_ad_lookup_job,
    create_ad_check_job as service_create_ad_check_job,
    create_ad_lookup_job as service_create_ad_lookup_job,
    get_ad_check_job as service_get_ad_check_job,
    get_ad_lookup_job as service_get_ad_lookup_job,
    get_pending_ad_check_jobs as service_get_pending_ad_check_jobs,
    get_pending_ad_lookup_jobs as service_get_pending_ad_lookup_jobs,
    list_ad_check_jobs as service_list_ad_check_jobs,
    submit_ad_check_job_result as service_submit_ad_check_job_result,
    submit_ad_lookup_job_result as service_submit_ad_lookup_job_result,
)
from app.services.ad_explorer import (
    ADExplorerBadRequest,
    ADExplorerConflict,
    ADExplorerNotFound,
    claim_ad_explorer_job as service_claim_ad_explorer_job,
    create_ad_explorer_job as service_create_ad_explorer_job,
    get_ad_explorer_job as service_get_ad_explorer_job,
    get_pending_ad_explorer_jobs as service_get_pending_ad_explorer_jobs,
    list_ad_explorer_jobs as service_list_ad_explorer_jobs,
    submit_ad_explorer_job_result as service_submit_ad_explorer_job_result,
)
from app.services.ad_snapshot import (
    ADSnapshotBadRequest,
    ADSnapshotNotFound,
    get_ad_snapshot as service_get_ad_snapshot,
    receive_ad_snapshot as service_receive_ad_snapshot,
)
from app.services.ad_admin import (
    ADAdminBadRequest,
    ADAdminConflict,
    ADAdminNotFound,
    claim_ad_admin_job as service_claim_ad_admin_job,
    create_ad_admin_job as service_create_ad_admin_job,
    get_ad_admin_job as service_get_ad_admin_job,
    get_pending_ad_admin_jobs as service_get_pending_ad_admin_jobs,
    list_ad_admin_jobs as service_list_ad_admin_jobs,
    submit_ad_admin_job_result as service_submit_ad_admin_job_result,
)


from app.services.worker_status import (
    WorkerStatusBadRequest,
    get_worker_status as service_get_worker_status,
    get_worker_events as service_get_worker_events,
    receive_worker_heartbeat as service_receive_worker_heartbeat,
)
from app.services.agent_runtime import (
    AgentRuntimeBadRequest,
    AgentRuntimeConflict,
    AgentRuntimeNotFound,
    AgentRuntimeStorageError,
    claim_request as service_claim_request,
    get_agent_config as service_get_agent_config,
    get_agent_status as service_get_agent_status,
    get_default_agent_config as service_get_default_agent_config,
    get_pending_requests as service_get_pending_requests,
    receive_agent_heartbeat as service_receive_agent_heartbeat,
    submit_agent_result as service_submit_agent_result,
    update_agent_config as service_update_agent_config,
)
from app.models import OnboardingRequest, AgentResult, ResetRequestsPayload, ClaimRequestPayload, ApprovalPayload, DepartmentTemplatePayload, RoleTemplatePayload, OffboardingRequest, ModificationRequest



# PACK B2.4 — Dépendances RBAC du portail
PORTAL_READ_ACCESS = require_roles(
    "Viewer",
    "Operator",
    "ADAdmin",
    "SecurityAdmin",
    "Auditor",
    "UltraAdmin",
)

OPERATOR_ACCESS = require_roles(
    "Operator",
    "UltraAdmin",
)

AD_ACCESS = require_roles(
    "ADAdmin",
    "UltraAdmin",
)

SECURITY_ACCESS = require_roles(
    "SecurityAdmin",
    "UltraAdmin",
)

AUDIT_ACCESS = require_roles(
    "Auditor",
    "UltraAdmin",
)

SECURITY_OR_API_KEY_ACCESS = require_roles_or_api_key(
    "SecurityAdmin",
    "UltraAdmin",
)

AGENT_MODE_READ_OR_API_KEY_ACCESS = require_roles_or_api_key(
    "ADAdmin",
    "SecurityAdmin",
    "UltraAdmin",
)


IDENTITY_UPDATE_STATUS_ACCESS = (
    require_identity_update_roles(
        "UltraAdmin",
    )
)


app = FastAPI(
    title="Enterprise IT Automation Suite",
    description="API MVP pour gérer les arrivées utilisateurs et les demandes Active Directory.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# STEP176_CORS_REACT_DEV
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://10.10.10.11:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://10.10.10.11:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

AGENT_STATUS_FILE = DATA_DIR / "agent-status.json"
WORKER_STATUS_FILE = DATA_DIR / "worker-status.json"
WORKER_EVENTS_FILE = DATA_DIR / "worker-events.jsonl"
AGENT_CONFIG_FILE = DATA_DIR / "agent-config.json"
AD_CHECK_JOBS_FILE = DATA_DIR / "ad-check-jobs.json"
AD_LOOKUP_JOBS_FILE = DATA_DIR / "ad-lookup-jobs.json"
AD_EXPLORER_JOBS_FILE = DATA_DIR / "ad-explorer-jobs.json"
AD_SNAPSHOT_FILE = DATA_DIR / "ad-snapshot.json"
AD_SNAPSHOT_EXPECTED_BASE_DN = os.getenv(
    "EITAS_AD_SNAPSHOT_BASE_DN",
    "OU=EITAS,DC=API,DC=LOCAL",
)
AD_SNAPSHOT_STALE_AFTER_SECONDS = max(
    3,
    int(os.getenv("EITAS_AD_SNAPSHOT_STALE_AFTER_SECONDS", "15")),
)
AD_DOMAIN_CATALOG_FILE = (
    DATA_DIR / "ad-domain-catalog.json"
)

AD_DOMAIN_CATALOG_EXPECTED_BASE_DN = os.getenv(
    "EITAS_AD_DOMAIN_CATALOG_BASE_DN",
    "DC=API,DC=LOCAL",
)

AD_DOMAIN_CATALOG_STALE_AFTER_SECONDS = max(
    5,
    int(
        os.getenv(
            "EITAS_AD_DOMAIN_CATALOG_STALE_AFTER_SECONDS",
            "30",
        )
    ),
)

AD_ADMIN_JOBS_FILE = DATA_DIR / "ad-admin-jobs.json"

IDENTITY_UPDATE_STATUS_FILE = Path(
    os.getenv(
        "EITAS_IDENTITY_UPDATE_STATUS_FILE",
        "/var/lib/eitas/identity-update/status.json",
    )
).resolve()

IDENTITY_UPDATE_SOURCE_CHECK_REQUEST_FILE = Path(
    os.getenv(
        "EITAS_IDENTITY_UPDATE_SOURCE_CHECK_REQUEST_FILE",
        "/var/lib/eitas/identity-update/requests/upstream-check.json",
    )
).resolve()



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
def get_templates(
    api_key: None = Depends(PORTAL_READ_ACCESS),
):
    return service_get_templates(TEMPLATES_FILE)


@app.post("/api/onboarding/request")
def create_onboarding_request(payload: OnboardingRequest, api_key: None = Depends(OPERATOR_ACCESS)):
    try:
        response, audit_event = service_create_onboarding_request(
            REQUESTS_FILE,
            TEMPLATES_FILE,
            payload,
        )
    except EmployeeLifecycleBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.get("/api/requests")
def list_requests(api_key: None = Depends(PORTAL_READ_ACCESS)):
    return service_list_requests(REQUESTS_FILE)


@app.get("/api/requests/{request_id}")
def get_request_by_id(request_id: str, api_key: None = Depends(PORTAL_READ_ACCESS)):
    try:
        return service_get_request_by_id(REQUESTS_FILE, request_id)
    except RequestNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/agent/config")
def get_agent_config(api_key: None = Depends(SECURITY_OR_API_KEY_ACCESS)):
    try:
        return service_get_agent_config(AGENT_CONFIG_FILE)
    except AgentRuntimeStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/agent/config")
def update_agent_config(payload: dict, api_key: None = Depends(SECURITY_OR_API_KEY_ACCESS)):
    try:
        response, audit_event = service_update_agent_config(AGENT_CONFIG_FILE, payload)
    except AgentRuntimeBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except AgentRuntimeStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if audit_event:
        write_audit_log(**audit_event)

    return response

@app.post("/api/agent/heartbeat")
def receive_agent_heartbeat(payload: dict, api_key: None = Depends(require_api_key)):
    return service_receive_agent_heartbeat(AGENT_STATUS_FILE, payload)

@app.get("/api/agent/status")
def get_agent_status(api_key: None = Depends(SECURITY_OR_API_KEY_ACCESS)):
    try:
        return service_get_agent_status(AGENT_STATUS_FILE)
    except AgentRuntimeStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/agent/worker-heartbeat")
def receive_worker_heartbeat(payload: dict = Body(...), api_key: None = Depends(require_api_key)):
    try:
        return service_receive_worker_heartbeat(WORKER_STATUS_FILE, payload, WORKER_EVENTS_FILE)
    except WorkerStatusBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/admin/worker-status")
def get_worker_status(api_key: None = Depends(SECURITY_ACCESS)):
    return service_get_worker_status(WORKER_STATUS_FILE, WORKER_EVENTS_FILE)


@app.get("/api/admin/worker-events")
def get_worker_events(limit: int = 100, api_key: None = Depends(SECURITY_ACCESS)):
    return service_get_worker_events(WORKER_EVENTS_FILE, limit=limit)

@app.get("/api/agent/pending")
def get_pending_requests(api_key: None = Depends(require_api_key)):
    return service_get_pending_requests(REQUESTS_FILE)

@app.post("/api/agent/claim/{request_id}")
def claim_request(request_id: str, payload: ClaimRequestPayload, api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_claim_request(
            REQUESTS_FILE,
            request_id,
            payload.agent_name or "unknown-agent",
        )
    except AgentRuntimeConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except AgentRuntimeNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response

@app.post("/api/agent/result/{request_id}")
def submit_agent_result(request_id: str, result: AgentResult, api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_submit_agent_result(
            REQUESTS_FILE,
            request_id,
            result.model_dump(),
        )
    except AgentRuntimeNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response

@app.post("/api/admin/requests/reset")
def reset_requests(payload: ResetRequestsPayload, api_key: None = Depends(OPERATOR_ACCESS)):
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
def retry_request(request_id: str, api_key: None = Depends(OPERATOR_ACCESS)):
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
def approve_request(request_id: str, payload: ApprovalPayload, api_key: None = Depends(OPERATOR_ACCESS)):
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
def reject_request(request_id: str, payload: ApprovalPayload, api_key: None = Depends(OPERATOR_ACCESS)):
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




def get_request_id_from_payload(value):
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        for key in ["id", "request_id"]:
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()

    return ""




@app.post("/api/ad-lookup/jobs")
def create_ad_lookup_job(payload: dict = Body(...), api_key: None = Depends(AD_ACCESS)):
    try:
        response, audit_event = service_create_ad_lookup_job(AD_LOOKUP_JOBS_FILE, payload)
    except ADJobsBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    write_audit_log(**audit_event)
    return response


@app.get("/api/ad-lookup/jobs/{job_id}")
def get_ad_lookup_job(job_id: str, api_key: None = Depends(AD_ACCESS)):
    try:
        return service_get_ad_lookup_job(AD_LOOKUP_JOBS_FILE, job_id)
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/agent/ad-lookup/pending")
def get_pending_ad_lookup_jobs(api_key: None = Depends(require_api_key)):
    return service_get_pending_ad_lookup_jobs(AD_LOOKUP_JOBS_FILE)


@app.post("/api/agent/ad-lookup/claim/{job_id}")
def claim_ad_lookup_job(job_id: str, payload: dict = Body(default={}), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_claim_ad_lookup_job(AD_LOOKUP_JOBS_FILE, job_id, payload)
    except ADJobsConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)
    return response


@app.post("/api/agent/ad-lookup/result/{job_id}")
def submit_ad_lookup_job_result(job_id: str, payload: dict = Body(...), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_submit_ad_lookup_job_result(AD_LOOKUP_JOBS_FILE, job_id, payload)
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)
    return response


@app.post("/api/ad-check/jobs")
def create_ad_check_job(payload: dict = Body(...), api_key: None = Depends(AD_ACCESS)):
    try:
        response, audit_event = service_create_ad_check_job(
            AD_CHECK_JOBS_FILE,
            REQUESTS_FILE,
            payload,
        )
    except ADJobsBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)
    return response


@app.get("/api/ad-check/jobs")
def list_ad_check_jobs(limit: int = 200, api_key: None = Depends(AD_ACCESS)):
    return service_list_ad_check_jobs(AD_CHECK_JOBS_FILE, limit)


@app.get("/api/ad-check/jobs/{job_id}")
def get_ad_check_job(job_id: str, api_key: None = Depends(AD_ACCESS)):
    try:
        return service_get_ad_check_job(AD_CHECK_JOBS_FILE, job_id)
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/agent/ad-check/pending")
def get_pending_ad_check_jobs(api_key: None = Depends(require_api_key)):
    return service_get_pending_ad_check_jobs(AD_CHECK_JOBS_FILE)


@app.post("/api/agent/ad-check/claim/{job_id}")
def claim_ad_check_job(job_id: str, payload: dict = Body(default={}), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_claim_ad_check_job(AD_CHECK_JOBS_FILE, job_id, payload)
    except ADJobsConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)
    return response


@app.post("/api/agent/ad-check/result/{job_id}")
def submit_ad_check_job_result(job_id: str, payload: dict = Body(...), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_submit_ad_check_job_result(AD_CHECK_JOBS_FILE, job_id, payload)
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)
    return response


@app.post("/api/agent/ad-snapshot")
def receive_ad_snapshot(
    payload: dict = Body(...),
    api_key: None = Depends(require_api_key),
):
    try:
        return service_receive_ad_snapshot(
            AD_SNAPSHOT_FILE,
            payload,
            expected_base_dn=AD_SNAPSHOT_EXPECTED_BASE_DN,
        )
    except ADSnapshotBadRequest as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.get("/api/ad-snapshot")
def get_ad_snapshot(
    api_key: None = Depends(AD_ACCESS),
):
    try:
        return service_get_ad_snapshot(
            AD_SNAPSHOT_FILE,
            stale_after_seconds=AD_SNAPSHOT_STALE_AFTER_SECONDS,
        )
    except ADSnapshotNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


@app.post(
    "/api/agent/ad-domain-catalog"
)
def receive_ad_domain_catalog(
    payload: dict = Body(...),
    api_key: None = Depends(
        require_api_key
    ),
):
    try:
        response = service_receive_ad_snapshot(
            AD_DOMAIN_CATALOG_FILE,
            payload,
            expected_base_dn=(
                AD_DOMAIN_CATALOG_EXPECTED_BASE_DN
            ),
        )

        response["message"] = (
            "Catalogue Active Directory "
            "du domaine enregistré."
        )

        return response

    except ADSnapshotBadRequest as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.get(
    "/api/ad-domain-catalog"
)
def get_ad_domain_catalog(
    api_key: None = Depends(AD_ACCESS),
):
    try:
        return service_get_ad_snapshot(
            AD_DOMAIN_CATALOG_FILE,
            stale_after_seconds=(
                AD_DOMAIN_CATALOG_STALE_AFTER_SECONDS
            ),
        )

    except ADSnapshotNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


@app.post("/api/ad-explorer/jobs")
def create_ad_explorer_job(payload: dict = Body(...), api_key: None = Depends(AD_ACCESS)):
    try:
        response, audit_event = service_create_ad_explorer_job(AD_EXPLORER_JOBS_FILE, payload)
    except ADExplorerBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.get("/api/ad-explorer/jobs")
def list_ad_explorer_jobs(limit: int = 100, api_key: None = Depends(AD_ACCESS)):
    return service_list_ad_explorer_jobs(AD_EXPLORER_JOBS_FILE, limit)


@app.get("/api/ad-explorer/jobs/{job_id}")
def get_ad_explorer_job(job_id: str, api_key: None = Depends(AD_ACCESS)):
    try:
        return service_get_ad_explorer_job(AD_EXPLORER_JOBS_FILE, job_id)
    except ADExplorerNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/agent/ad-explorer/pending")
def get_pending_ad_explorer_jobs(api_key: None = Depends(require_api_key)):
    return service_get_pending_ad_explorer_jobs(AD_EXPLORER_JOBS_FILE)


@app.post("/api/agent/ad-explorer/claim/{job_id}")
def claim_ad_explorer_job(job_id: str, payload: dict = Body(default={}), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_claim_ad_explorer_job(AD_EXPLORER_JOBS_FILE, job_id, payload)
    except ADExplorerConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ADExplorerNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.post("/api/agent/ad-explorer/result/{job_id}")
def submit_ad_explorer_job_result(job_id: str, payload: dict = Body(...), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_submit_ad_explorer_job_result(AD_EXPLORER_JOBS_FILE, job_id, payload)
    except ADExplorerNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.post("/api/ad-admin/jobs")
def create_ad_admin_job(payload: dict = Body(...), api_key: None = Depends(AD_ACCESS)):
    try:
        response, audit_event = service_create_ad_admin_job(AD_ADMIN_JOBS_FILE, payload)
    except ADAdminBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.get("/api/ad-admin/jobs")
def list_ad_admin_jobs(limit: int = 100, api_key: None = Depends(AD_ACCESS)):
    return service_list_ad_admin_jobs(AD_ADMIN_JOBS_FILE, limit)


@app.get("/api/ad-admin/jobs/{job_id}")
def get_ad_admin_job(job_id: str, api_key: None = Depends(AD_ACCESS)):
    try:
        return service_get_ad_admin_job(AD_ADMIN_JOBS_FILE, job_id)
    except ADAdminNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/agent/ad-admin/pending")
def get_pending_ad_admin_jobs(api_key: None = Depends(require_api_key)):
    return service_get_pending_ad_admin_jobs(AD_ADMIN_JOBS_FILE)


@app.post("/api/agent/ad-admin/claim/{job_id}")
def claim_ad_admin_job(job_id: str, payload: dict = Body(default={}), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_claim_ad_admin_job(AD_ADMIN_JOBS_FILE, job_id, payload)
    except ADAdminConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ADAdminNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.post("/api/agent/ad-admin/result/{job_id}")
def submit_ad_admin_job_result(job_id: str, payload: dict = Body(...), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_submit_ad_admin_job_result(AD_ADMIN_JOBS_FILE, job_id, payload)
    except ADAdminNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.get("/api/identity-update/status")
def get_identity_update_status(
    _identity=Depends(
        IDENTITY_UPDATE_STATUS_ACCESS
    ),
):
    try:
        return service_get_identity_update_status(
            IDENTITY_UPDATE_STATUS_FILE
        )
    except IdentityUpdateStatusUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@app.post(
    "/api/identity-update/source-check",
    status_code=202,
)
def request_identity_update_source_check(
    identity=Depends(
        IDENTITY_UPDATE_STATUS_ACCESS
    ),
):
    try:
        response = (
            service_create_identity_update_source_check_request(
                IDENTITY_UPDATE_SOURCE_CHECK_REQUEST_FILE,
                identity.username,
            )
        )
    except IdentityUpdateRequestConflict as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except IdentityUpdateRequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    write_audit_log(
        "identity_update_source_check_requested",
        actor=identity.username,
        details={
            "request_id": response["request_id"],
            "action": response["action"],
        },
        message=(
            "Vérification de la source upstream demandée"
        ),
    )

    return response


@app.get("/api/audit-logs")
def list_audit_logs(limit: int = 50, api_key: None = Depends(AUDIT_ACCESS)):
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
def admin_get_templates(api_key: None = Depends(SECURITY_ACCESS)):
    return service_get_templates(TEMPLATES_FILE)


@app.post("/api/admin/templates/departments")
def upsert_department_template(payload: DepartmentTemplatePayload, api_key: None = Depends(SECURITY_ACCESS)):
    response, audit_event = service_upsert_department_template(
        TEMPLATES_FILE,
        payload.name,
        payload.default_ou,
        payload.default_groups,
    )

    write_audit_log(**audit_event)

    return response


@app.delete("/api/admin/templates/departments/{department_name}")
def delete_department_template(department_name: str, api_key: None = Depends(SECURITY_ACCESS)):
    try:
        response, audit_event = service_delete_department_template(TEMPLATES_FILE, department_name)
    except TemplatesNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.post("/api/admin/templates/departments/{department_name}/roles")
def upsert_role_template(department_name: str, payload: RoleTemplatePayload, api_key: None = Depends(SECURITY_ACCESS)):
    try:
        response, audit_event = service_upsert_role_template(
            TEMPLATES_FILE,
            department_name,
            payload.name,
            payload.groups,
        )
    except TemplatesNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.delete("/api/admin/templates/departments/{department_name}/roles/{role_name}")
def delete_role_template(department_name: str, role_name: str, api_key: None = Depends(SECURITY_ACCESS)):
    try:
        response, audit_event = service_delete_role_template(
            TEMPLATES_FILE,
            department_name,
            role_name,
        )
    except TemplatesNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.post("/api/offboarding/request")
def create_offboarding_request(payload: OffboardingRequest, api_key: None = Depends(OPERATOR_ACCESS)):
    response, audit_event = service_create_offboarding_request(
        REQUESTS_FILE,
        payload,
    )

    write_audit_log(**audit_event)

    return response


@app.post("/api/modification/request")
def create_modification_request(payload: ModificationRequest, api_key: None = Depends(OPERATOR_ACCESS)):
    response, audit_event = service_create_modification_request(
        REQUESTS_FILE,
        payload,
    )

    write_audit_log(**audit_event)

    return response


# STEP176_AGENT_MODE_COMPAT_ROUTES
def _eitas_agent_mode_config_file():
    if "AGENT_CONFIG_FILE" in globals():
        return AGENT_CONFIG_FILE

    if "DATA_DIR" in globals():
        return DATA_DIR / "agent_config.json"

    return Path(__file__).resolve().parent.parent / "data" / "agent_config.json"


def _eitas_agent_mode_load_config():
    path = _eitas_agent_mode_config_file()

    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)

            if isinstance(data, dict):
                return data
    except Exception:
        return {}

    return {}


def _eitas_agent_mode_save_config(config):
    path = _eitas_agent_mode_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, ensure_ascii=False)


def _eitas_agent_mode_normalize(value):
    text = str(value or "Simulation").strip().lower()

    if text in {"production", "prod", "reel", "réel", "real"}:
        return "Production"

    return "Simulation"


@app.get("/api/agent/mode")
def eitas_get_agent_mode_compat(
    api_key: None = Depends(
        AGENT_MODE_READ_OR_API_KEY_ACCESS
    ),
):
    config = _eitas_agent_mode_load_config()
    mode = _eitas_agent_mode_normalize(
        config.get("mode") or
        config.get("Mode") or
        "Simulation"
    )

    return {
        "mode": mode,
        "source": "agent_config"
    }


@app.post("/api/admin/agent/mode")
def eitas_update_agent_mode_compat(
    payload: dict = Body(...),
    api_key: None = Depends(SECURITY_ACCESS),
):
    wanted_mode = _eitas_agent_mode_normalize(payload.get("mode") if isinstance(payload, dict) else None)
    updated_by = payload.get("updated_by") if isinstance(payload, dict) else None

    config = _eitas_agent_mode_load_config()
    config["mode"] = wanted_mode
    config["Mode"] = wanted_mode
    config["updated_by"] = updated_by or "react-admin"
    config["updated_at"] = now_iso() if "now_iso" in globals() else ""

    _eitas_agent_mode_save_config(config)

    if "write_audit_log" in globals():
        try:
            write_audit_log(
                "agent_mode_updated",
                actor=updated_by or "react-admin",
                details={"mode": wanted_mode},
                message=f"Mode agent mis à jour : {wanted_mode}"
            )
        except Exception:
            pass

    return {
        "mode": wanted_mode,
        "message": f"Mode agent mis à jour : {wanted_mode}"
    }
