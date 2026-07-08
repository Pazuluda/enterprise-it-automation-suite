from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

TEMPLATES_FILE = DATA_DIR / "templates.json"
REQUESTS_FILE = DATA_DIR / "requests.json"
AUDIT_FILE = DATA_DIR / "audit.jsonl"

API_KEY = os.getenv("EITAS_API_KEY", "dev-local-key-change-me")
