"""Load field schemas and validate structured (repeatable/composite) answers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models import InputType
from app.services.question_store import UnifiedQuestionRecord, load_unified_questions

_SCHEMAS_DIR = Path(__file__).parent.parent / "data" / "schemas"

PRIMARY_ORG_REF = "primary"
SYNTHETIC_FIELDS = frozenset({"organisation_id"})

ORG_FIELD_IDS = (
    "org-name",
    "org-type",
    "org-id",
    "org-addr-street",
    "org-addr-city",
    "org-addr-postcode",
    "org-addr-state",
    "org-addr-country",
    "org-website",
    "org-commercial-purpose",
    "org-commercial-evidence-types",
    "org-commercial-evidence",
)


def _read_schema(name: str) -> dict[str, Any]:
    path = _SCHEMAS_DIR / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Unknown schema: {name}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_schema(name: str) -> dict[str, Any]:
    return _read_schema(name)


def list_schema_names() -> list[str]:
    if not _SCHEMAS_DIR.is_dir():
        return []
    return sorted(p.stem for p in _SCHEMAS_DIR.glob("*.json"))


def _questions_by_id() -> dict[str, UnifiedQuestionRecord]:
    return {q.id: q for q in load_unified_questions()}


def resolve_field_metadata(field_id: str) -> dict[str, Any] | None:
    if field_id == "organisation_id":
        return {
            "id": "organisation_id",
            "text_en": "Organisation",
            "type": "organisation_ref",
            "granularity": "general",
        }
    record = _questions_by_id().get(field_id)
    if not record:
        return None
    meta: dict[str, Any] = {
        "id": record.id,
        "text_en": record.text,
        "type": record.input_type.value,
        "help": record.help_text,
        "config": record.config,
        "options": (record.config or {}).get("options"),
        "granularity": record.granularity or "general",
    }
    if record.input_type == InputType.ISO_3166_1:
        from pycountry import countries

        meta["options"] = sorted(c.name for c in countries)
    if field_id == "data-requested":
        from app.core.platform_specific import META_DATA_REQUESTED_HELP

        meta["help"] = None
        meta["platform_help"] = {"meta": META_DATA_REQUESTED_HELP}
    return meta


def schema_field_metadata(
    schema_name: str,
    *,
    vlopses: list[str] | None = None,
) -> list[dict[str, Any]]:
    schema = load_schema(schema_name)
    if "fields" in schema:
        fields = schema["fields"]
    elif "sections" in schema:
        fields = []
        for section in schema["sections"]:
            sub = load_schema(section["schema"])
            fields.extend(sub.get("fields", []))
    else:
        fields = []
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for field_id in fields:
        if field_id in seen:
            continue
        seen.add(field_id)
        meta = resolve_field_metadata(field_id)
        if meta:
            if vlopses and meta.get("granularity") == "platform_specific":
                from app.core.config import get_vlopse_configuration_for
                from app.core.platform_specific import (
                    format_platform_placeholder,
                    vlopses_mapping_general,
                )

                scoped = vlopses_mapping_general(vlopses, field_id)
                meta["scoped_platforms"] = scoped
                platform_names = [
                    get_vlopse_configuration_for(v).info.name for v in scoped
                ]
                meta["text_en"] = format_platform_placeholder(
                    str(meta["text_en"]), platform_names
                )
            result.append(meta)
    return result


def _validate_leaf(field_id: str, value: Any) -> str | None:
    if field_id == "organisation_id":
        if value is None or str(value).strip() == "":
            return "Organisation reference is required"
        return None
    record = _questions_by_id().get(field_id)
    if not record:
        return f"Unknown field '{field_id}'"
    if value is None:
        return None
    if isinstance(value, dict):
        for scoped_val in value.values():
            if scoped_val is None or (isinstance(scoped_val, str) and not scoped_val.strip()):
                continue
            config = record.parsed_config
            if config:
                error = config.validate_answer(scoped_val)
                if error:
                    return error
        return None
    if isinstance(value, list):
        config = record.parsed_config
        if config:
            return config.validate_answer(value)
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    config = record.parsed_config
    if config:
        return config.validate_answer(value)
    return None


def _validate_item_fields(
    item: dict[str, Any],
    field_ids: list[str],
    *,
    path: str,
) -> str | None:
    for field_id in field_ids:
        if field_id not in item and field_id not in SYNTHETIC_FIELDS:
            continue
        error = _validate_leaf(field_id, item.get(field_id))
        if error:
            return f"{path}.{field_id}: {error}"
    return None


def _known_org_ids(
    team_orgs: list[dict[str, Any]],
    *,
    allow_primary: bool,
) -> set[str]:
    ids = {str(item.get("id", "")).strip() for item in team_orgs if item.get("id")}
    if allow_primary:
        ids.add(PRIMARY_ORG_REF)
    return {i for i in ids if i}


def _validate_affiliation_refs(
    affiliations: list[dict[str, Any]],
    known_orgs: set[str],
    *,
    path: str,
) -> str | None:
    aff_fields = load_schema("affiliation-profile")["fields"]
    for idx, aff in enumerate(affiliations):
        error = _validate_item_fields(aff, aff_fields, path=f"{path}[{idx}]")
        if error:
            return error
        org_id = str(aff.get("organisation_id", "")).strip()
        if org_id and org_id not in known_orgs:
            return f"{path}[{idx}].organisation_id: unknown organisation '{org_id}'"
    return None


def validate_composite_answer(
    raw_value: str,
    *,
    schema_name: str,
) -> str | None:
    if not raw_value or not raw_value.strip():
        return None
    try:
        item = json.loads(raw_value)
    except json.JSONDecodeError:
        return "Invalid JSON structure"
    if not isinstance(item, dict):
        return "Expected a JSON object"

    schema = load_schema(schema_name)
    if "fields" not in schema:
        return f"Unsupported composite schema '{schema_name}'"
    return _validate_item_fields(item, schema["fields"], path="")


def validate_repeatable_answer(
    raw_value: str,
    *,
    schema_name: str,
    min_items: int = 0,
    max_items: int | None = None,
    team_orgs_raw: str | None = None,
) -> str | None:
    if not raw_value or not raw_value.strip():
        if min_items > 0:
            return f"At least {min_items} item(s) required"
        return None
    try:
        items = json.loads(raw_value)
    except json.JSONDecodeError:
        return "Invalid JSON structure"
    if not isinstance(items, list):
        return "Expected a JSON array"

    if len(items) < min_items:
        return f"At least {min_items} item(s) required"
    if max_items is not None and len(items) > max_items:
        return f"At most {max_items} item(s) allowed"

    schema = load_schema(schema_name)
    team_orgs: list[dict[str, Any]] = []
    if team_orgs_raw:
        try:
            parsed = json.loads(team_orgs_raw)
            if isinstance(parsed, list):
                team_orgs = parsed
        except json.JSONDecodeError:
            pass

    if "fields" in schema:
        field_ids = schema["fields"]
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                return f"Item {idx} must be an object"
            if schema_name == "organisation-profile" and "id" not in item:
                return f"Item {idx} must include an 'id'"
            error = _validate_item_fields(item, field_ids, path=f"[{idx}]")
            if error:
                return error
        return None

    if "sections" in schema:
        known_orgs = _known_org_ids(team_orgs, allow_primary=True)
        person_fields = load_schema("person-profile")["fields"]
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                return f"Item {idx} must be an object"
            person = item.get("person")
            if not isinstance(person, dict):
                return f"Item {idx} must include a 'person' object"
            error = _validate_item_fields(person, person_fields, path=f"[{idx}].person")
            if error:
                return error
            affiliations = item.get("affiliations")
            if not isinstance(affiliations, list):
                return f"Item {idx} must include an 'affiliations' array"
            min_aff = 1
            for section in schema["sections"]:
                if section.get("key") == "affiliations":
                    min_aff = int(section.get("min_items", 1))
            if len(affiliations) < min_aff:
                return f"Item {idx} needs at least {min_aff} affiliation(s)"
            error = _validate_affiliation_refs(
                affiliations, known_orgs, path=f"[{idx}].affiliations"
            )
            if error:
                return error
        return None

    return f"Unsupported schema '{schema_name}'"
