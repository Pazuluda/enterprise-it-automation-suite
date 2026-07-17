from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]


def _get_data_dir() -> Path:
    configured = os.getenv("EITAS_DATA_DIR", "").strip()

    if not configured:
        return (BASE_DIR / "data").resolve()

    candidate = Path(configured).expanduser()

    if not candidate.is_absolute():
        raise RuntimeError(
            "EITAS_DATA_DIR doit être un chemin absolu."
        )

    return candidate.resolve()


DATA_DIR = _get_data_dir()

TEMPLATES_FILE = DATA_DIR / "templates.json"
REQUESTS_FILE = DATA_DIR / "requests.json"
AUDIT_FILE = DATA_DIR / "audit.jsonl"

API_KEY = os.getenv("EITAS_API_KEY", "dev-local-key-change-me")
