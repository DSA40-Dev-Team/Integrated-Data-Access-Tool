"""File-backed question storage (source of truth under app/data/)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models import InputType
from app.schemas import ConstraintConfig, config_adapter

_DATA_ROOT = Path(__file__).parent.parent / "data"
UNIFIED_QUESTIONS_PATH = _DATA_ROOT / "questions_all.json"
UNIFIED_QUESTIONS_FALLBACK = _DATA_ROOT / "questions.json"
PLATFORM_QUESTIONS_DIR = _DATA_ROOT / "questions"

CSV_TYPE_TO_INPUT: dict[str, InputType] = {
    "free form": InputType.text,
    "selection": InputType.selection,
    "file upload": InputType.file_upload,
    "date-select": InputType.date_select,
    "multi-select": InputType.multi_select,
}

JSON_TYPE_TO_INPUT: dict[str, InputType] = {
    "text": InputType.text,
    "selection": InputType.selection,
    "file_upload": InputType.file_upload,
    "date_select": InputType.date_select,
    "multi_select": InputType.multi_select,
    "iso-3166-1": InputType.ISO_3166_1,
    "orcid": InputType.orcid,
    "repeatable_group": InputType.repeatable_group,
    "composite_group": InputType.composite_group,
}

COUNTRY_SHORTHANDS = frozenset({"researcher-addr-country", "org-addr-country"})


@dataclass
class UnifiedQuestionRecord:
    id: str
    text: str
    input_type: InputType
    help_text: str | None = None
    config: dict[str, Any] | None = None
    category: str | None = None
    granularity: str | None = None

    @property
    def parsed_config(self) -> ConstraintConfig | None:
        normalized = normalize_config(self.config, self.input_type)
        if normalized:
            return config_adapter.validate_python(normalized)
        return None


@dataclass
class PlatformQuestionRecord:
    id: str
    text: str
    vlopse: str
    required: bool
    input_type: InputType
    details: str | None = None
    config: dict[str, Any] | None = None
    classification: str | None = None


def parse_options(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        return []
    if "; " in raw:
        return [part.strip() for part in raw.split("; ") if part.strip()]
    return [part.strip() for part in raw.split(", ") if part.strip()]


def normalize_config(
    config: dict[str, Any] | None, input_type: InputType
) -> dict[str, Any] | None:
    if not config:
        if input_type == InputType.ISO_3166_1:
            return {"type": "iso-3166-1"}
        if input_type == InputType.orcid:
            return {"type": "orcid"}
        return None
    out = dict(config)
    if "i_type" in out and "type" not in out:
        out["type"] = out.pop("i_type")
    if input_type == InputType.multi_select and out.get("type") == "selection":
        out["type"] = "multi_select"
    return out


def _build_config_from_row(
    shorthand: str,
    csv_type: str,
    input_type: InputType,
    options: list[str],
    raw_config: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if raw_config:
        return normalize_config(raw_config, input_type)
    if input_type == InputType.ISO_3166_1:
        return {"type": "iso-3166-1"}
    if input_type == InputType.orcid:
        return {"type": "orcid"}
    if input_type == InputType.selection and options:
        return {"type": "selection", "options": options}
    if input_type == InputType.multi_select and options:
        return {"type": "multi_select", "options": options}
    if csv_type == "selection" and shorthand in COUNTRY_SHORTHANDS and not options:
        return {"type": "iso-3166-1"}
    return None


def unified_from_json(row: dict[str, Any]) -> UnifiedQuestionRecord:
    shorthand = str(row["id"]).strip()
    raw_type = str(row.get("type") or "text").strip().lower()
    csv_type = raw_type.replace("_", " ")
    if raw_type in JSON_TYPE_TO_INPUT:
        input_type = JSON_TYPE_TO_INPUT[raw_type]
    elif csv_type in CSV_TYPE_TO_INPUT:
        input_type = CSV_TYPE_TO_INPUT[csv_type]
    else:
        raise ValueError(f"{shorthand}: unknown type {row.get('type')!r}")

    options = row.get("options")
    if isinstance(options, list):
        option_list = [str(o) for o in options]
    else:
        option_list = parse_options(str(options or ""))

    if (
        raw_type == "selection"
        and shorthand in COUNTRY_SHORTHANDS
        and not option_list
        and not row.get("config")
    ):
        input_type = InputType.ISO_3166_1

    config = _build_config_from_row(
        shorthand,
        csv_type,
        input_type,
        option_list,
        row.get("config"),
    )
    help_text = (row.get("help") or row.get("help_text") or row.get("comments") or "")
    help_text = str(help_text).strip() or None

    return UnifiedQuestionRecord(
        id=shorthand,
        text=str(row.get("text_en") or row.get("text") or row.get("question_en") or ""),
        input_type=input_type,
        help_text=help_text,
        config=config,
        category=row.get("category"),
        granularity=row.get("granularity"),
    )


def unified_to_json(record: UnifiedQuestionRecord) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": record.id,
        "text_en": record.text,
        "type": record.input_type.value,
        "granularity": record.granularity or "general",
    }
    if record.category:
        row["category"] = record.category
    if record.help_text:
        row["help"] = record.help_text
    if record.config:
        row["config"] = record.config
        opts = record.config.get("options")
        if opts and record.config.get("type") in {"selection", "multi_select"}:
            row["options"] = opts
    return row


def _parse_required(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().upper()
    if text in {"TRUE", "1", "YES"}:
        return True
    if text in {"FALSE", "0", "NO", "N/A", ""}:
        return False
    return text == "TRUE"


def _combine_details(row: dict[str, Any]) -> str | None:
    parts = [
        str(row.get("Details") or row.get("details") or "").strip(),
        str(row.get("Comments") or row.get("comments") or "").strip(),
    ]
    parts = [p for p in parts if p]
    return "\n".join(parts) if parts else None


def platform_from_legacy_csv_row(row: dict[str, Any], vlopse: str) -> PlatformQuestionRecord:
    qid = str(row["id"]).strip()
    csv_type = str(row.get("Type") or row.get("type") or "free form").strip().lower()
    if csv_type not in CSV_TYPE_TO_INPUT:
        raise ValueError(f"{vlopse}/{qid}: unknown type {row.get('Type')!r}")
    input_type = CSV_TYPE_TO_INPUT[csv_type]
    options = parse_options(str(row.get("Options") or row.get("options") or ""))
    config = _build_config_from_row(qid, csv_type, input_type, options, row.get("config"))
    return PlatformQuestionRecord(
        id=qid,
        text=str(row.get("Question") or row.get("text") or "").strip(),
        vlopse=vlopse,
        required=_parse_required(row.get("Required") or row.get("required") or "FALSE"),
        input_type=input_type,
        details=_combine_details(row),
        config=config,
        classification=(row.get("Classification") or row.get("classification")),
    )


def platform_from_json(row: dict[str, Any], vlopse: str) -> PlatformQuestionRecord:
    if "Question" in row or "Type" in row:
        return platform_from_legacy_csv_row(row, vlopse)

    raw_type = str(row.get("input_type") or row.get("type") or "text")
    if raw_type in JSON_TYPE_TO_INPUT:
        input_type = JSON_TYPE_TO_INPUT[raw_type]
    else:
        csv_type = raw_type.lower()
        input_type = CSV_TYPE_TO_INPUT.get(csv_type, InputType.text)

    return PlatformQuestionRecord(
        id=str(row["id"]).strip(),
        text=str(row.get("text") or "").strip(),
        vlopse=vlopse,
        required=_parse_required(row.get("required", True)),
        input_type=input_type,
        details=row.get("details"),
        config=normalize_config(row.get("config"), input_type),
        classification=row.get("classification"),
    )


def platform_to_json(record: PlatformQuestionRecord) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": record.id,
        "text": record.text,
        "required": record.required,
        "input_type": record.input_type.value,
        "details": record.details,
        "config": record.config,
    }
    if record.classification:
        row["classification"] = record.classification
    return row


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_list(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def platform_questions_path(vlopse: str) -> Path:
    return PLATFORM_QUESTIONS_DIR / f"{vlopse}.json"


def load_unified_questions() -> list[UnifiedQuestionRecord]:
    path = (
        UNIFIED_QUESTIONS_PATH
        if UNIFIED_QUESTIONS_PATH.is_file()
        else UNIFIED_QUESTIONS_FALLBACK
    )
    if not path.is_file():
        return []
    return [unified_from_json(row) for row in _read_json_list(path)]


def save_unified_questions(records: list[UnifiedQuestionRecord]) -> None:
    rows = [unified_to_json(r) for r in records]
    _write_json_list(UNIFIED_QUESTIONS_PATH, rows)
    _write_json_list(UNIFIED_QUESTIONS_FALLBACK, rows)


def load_platform_questions(vlopse: str) -> list[PlatformQuestionRecord]:
    path = platform_questions_path(vlopse)
    if not path.is_file():
        return []
    return [platform_from_json(row, vlopse) for row in _read_json_list(path)]


def save_platform_questions(vlopse: str, records: list[PlatformQuestionRecord]) -> None:
    path = PLATFORM_QUESTIONS_DIR / f"{vlopse}.json"
    rows = [platform_to_json(r) for r in records]
    _write_json_list(path, rows)


def find_platform_question(vlopse: str, question_id: str) -> PlatformQuestionRecord | None:
    for record in load_platform_questions(vlopse):
        if record.id == question_id:
            return record
    return None


def find_platform_question_global(question_id: str) -> PlatformQuestionRecord | None:
    vlopses_dir = _DATA_ROOT / "vlopses"
    if not vlopses_dir.is_dir():
        return None
    for config_path in sorted(vlopses_dir.glob("*.json")):
        if config_path.stem == "platform_info":
            continue
        found = find_platform_question(config_path.stem, question_id)
        if found:
            return found
    return None
