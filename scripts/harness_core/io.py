"""JSON persistence helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonStore:
    @staticmethod
    def read_object(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON at {path}: {exc}") from exc

    @staticmethod
    def write(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

