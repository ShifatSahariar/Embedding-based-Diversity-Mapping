"""Run-state and artifact storage for SpreadEx tool mode."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import RUNS_ROOT


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_run_json(run_id: str, filename: str, data: dict[str, Any]) -> None:
    run_root = RUNS_ROOT / run_id
    safe_mkdir(run_root)
    (run_root / filename).write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_run_json(run_id: str, filename: str) -> dict[str, Any]:
    return json.loads((RUNS_ROOT / run_id / filename).read_text(encoding="utf-8"))


@dataclass
class RunState:
    run_id: str
    created_at: str
    status: str = "queued"
    step: str = "queued"
    logs: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def log(self, msg: str) -> None:
        self.logs.append(msg)
