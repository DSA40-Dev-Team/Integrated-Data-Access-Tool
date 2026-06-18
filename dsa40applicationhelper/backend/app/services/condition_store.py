"""File-backed general (unified form) visibility rules."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.models import Condition

_GENERAL_CONDITIONS_PATH = (
    Path(__file__).parent.parent / "data" / "general_conditions.json"
)


def load_general_conditions() -> dict[str, list[list[Condition]]]:
    if not _GENERAL_CONDITIONS_PATH.is_file():
        return {}
    raw = json.loads(_GENERAL_CONDITIONS_PATH.read_text(encoding="utf-8"))
    result: dict[str, list[list[Condition]]] = {}
    for general_id, groups in raw.items():
        parsed_groups: list[list[Condition]] = []
        for group in groups:
            parsed_groups.append([Condition.model_validate(c) for c in group])
        result[general_id] = parsed_groups
    return result
