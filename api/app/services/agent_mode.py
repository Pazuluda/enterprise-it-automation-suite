from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def normalize_agent_mode(value: Any) -> str:
    text = str(value or "Simulation").strip().lower()

    if text in {"production", "prod", "reel", "réel", "real"}:
        return "Production"

    return "Simulation"


def load_agent_mode_config(config_file: Path) -> dict:
    try:
        if config_file.exists():
            with config_file.open("r", encoding="utf-8") as handle:
                data = json.load(handle)

            if isinstance(data, dict):
                return data
    except Exception:
        return {}

    return {}


def save_agent_mode_config(config_file: Path, config: dict) -> None:
    config_file.parent.mkdir(parents=True, exist_ok=True)

    with config_file.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, ensure_ascii=False)


def get_agent_mode(config_file: Path) -> str:
    config = load_agent_mode_config(config_file)

    return normalize_agent_mode(
        config.get("mode")
        or config.get("Mode")
        or "Simulation"
    )


def update_agent_mode_config(
    config_file: Path,
    mode: Any,
    updated_by: str | None = None,
    updated_at: str | None = None,
) -> dict:
    wanted_mode = normalize_agent_mode(mode)

    config = load_agent_mode_config(config_file)
    config["mode"] = wanted_mode
    config["Mode"] = wanted_mode
    config["updated_by"] = updated_by or "react-admin"

    if updated_at is not None:
        config["updated_at"] = updated_at

    save_agent_mode_config(config_file, config)

    return config
