from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


APP_DIR = Path.home() / ".xhs_ecom_note_assistant"
DATA_DIR = APP_DIR / "data"
STATE_DIR = APP_DIR / "states"
LOG_DIR = APP_DIR / "logs"
CONFIG_FILE = APP_DIR / "config.json"
DB_FILE = DATA_DIR / "xhs_ecom.db"

for directory in (APP_DIR, DATA_DIR, STATE_DIR, LOG_DIR):
    directory.mkdir(parents=True, exist_ok=True)


@dataclass
class AppConfig:
    api_base: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4.1-mini"
    request_timeout: int = 60
    headless: bool = False
    attach_failure_policy: str = "stop"
    publish_timeout_ms: int = 60_000
    schedule_check_seconds: int = 30

    @classmethod
    def load(cls) -> "AppConfig":
        if not CONFIG_FILE.exists():
            return cls()
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            defaults = asdict(cls())
            return cls(**{key: raw.get(key, value) for key, value in defaults.items()})
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self) -> None:
        CONFIG_FILE.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
