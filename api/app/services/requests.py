from __future__ import annotations

from pathlib import Path

from app.core.storage import load_json


class RequestsError(Exception):
    pass


class RequestNotFound(RequestsError):
    pass


def list_requests(requests_file: Path) -> list[dict]:
    return load_json(requests_file, [])


def get_request_by_id(requests_file: Path, request_id: str) -> dict:
    requests = list_requests(requests_file)

    for request in requests:
        if request.get("id") == request_id:
            return request

    raise RequestNotFound("Demande introuvable")
