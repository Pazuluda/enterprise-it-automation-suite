import json
from datetime import datetime

from app.core.config import DATA_DIR, AUDIT_FILE


def write_audit_log(
    action: str,
    request_id: str | None = None,
    actor: str = "system",
    message: str = "",
    details: dict | None = None
):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": action,
        "request_id": request_id,
        "actor": actor,
        "message": message,
        "details": details or {}
    }

    with AUDIT_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")
