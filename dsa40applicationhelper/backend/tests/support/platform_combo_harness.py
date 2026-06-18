"""Shared helpers for platform-combination API integration tests."""

from __future__ import annotations

import json
from itertools import combinations
from typing import Any

from fastapi.testclient import TestClient

from app.core.platform_specific import vlopses_mapping_general
from app.core.schema_registry import composite_field_map
from app.core.structured_schemas import load_schema
from app.models import InputType
from app.services.question_store import UnifiedQuestionRecord, load_unified_questions
from app.services.vlopse import VlopseConfigService

_QUESTIONS_BY_ID: dict[str, UnifiedQuestionRecord] = {
    q.id: q for q in load_unified_questions()
}
_COMPOSITE_FIELDS = composite_field_map()


def platform_ids() -> list[str]:
    return VlopseConfigService().get_all()


def combos_56() -> list[list[str]]:
    ids = platform_ids()
    result: list[list[str]] = [[p] for p in ids]
    result.extend([list(c) for c in combinations(ids, 2)])
    result.append(ids)
    return result


def _leaf_value(record: UnifiedQuestionRecord) -> str:
    config = record.config or {}
    options = config.get("options") or []
    input_type = record.input_type

    if input_type == InputType.ISO_3166_1:
        return "Germany"
    if input_type == InputType.orcid:
        return "0000-0002-1825-0097"
    if input_type == InputType.date_select:
        if record.id == "tom-storage-end":
            return "2026-01-15"
        return "2025-01-15"
    if input_type == InputType.file_upload:
        return "/tmp/file.pdf"
    if input_type == InputType.multi_select:
        return "; ".join(options[:2]) if options else "topic a; topic b"
    if input_type == InputType.selection:
        return str(options[0]) if options else "Yes"
    if record.id == "collab-list":
        return "collab1@uni.edu; collab2@uni.edu"
    return "Sample description for integration testing."


def sample_field_value(field_id: str, vlopses: list[str]) -> Any:
    if field_id == "organisation_id":
        return "primary"

    record = _QUESTIONS_BY_ID.get(field_id)
    if record is None:
        return "Sample description for integration testing."

    if record.granularity == "platform_specific":
        scoped = vlopses_mapping_general(vlopses, field_id) or vlopses
        value = _leaf_value(record)
        return {platform: value for platform in scoped}

    return _leaf_value(record)


def composite_payload(composite_id: str, vlopses: list[str]) -> dict[str, Any]:
    return {
        field_id: sample_field_value(field_id, vlopses)
        for field_id in _COMPOSITE_FIELDS.get(composite_id, ())
    }


def sample_question_value(question: dict[str, Any], vlopses: list[str]) -> str:
    input_type = question["input_type"]

    if input_type == "composite_group":
        return json.dumps(composite_payload(question["id"], vlopses))

    if input_type == "repeatable_group":
        schema_name = (question.get("config") or {}).get("schema", "")
        if schema_name == "funding-entry-profile":
            item = {
                field_id: sample_field_value(field_id, vlopses)
                for field_id in load_schema(schema_name)["fields"]
            }
            return json.dumps([item])
        return "[]"

    options = question.get("options") or (question.get("config") or {}).get("options") or []
    if input_type == "iso-3166-1":
        return "Germany"
    if input_type == "date_select":
        return "2025-01-15"
    if input_type == "file_upload":
        return "/tmp/file.pdf"
    if input_type == "multi_select":
        return "; ".join(options[:2]) if options else "topic a; topic b"
    if input_type == "selection":
        return str(options[0]) if options else "Yes"
    return "Sample description for integration testing."


def build_answers(client: TestClient, vlopses: list[str]) -> list[dict[str, str]]:
    response = client.get("/api/questions", params={"vlopse": vlopses})
    response.raise_for_status()
    questions = response.json()
    return [
        {
            "question_id": question["id"],
            "value": sample_question_value(question, vlopses),
        }
        for question in questions
    ]


def validate_combo(client: TestClient, vlopses: list[str]) -> dict[str, Any]:
    payload = {"answers": build_answers(client, vlopses)}
    response = client.post("/api/validate", params={"vlopse": vlopses}, json=payload)
    response.raise_for_status()
    return response.json()


def transform_combo(client: TestClient, vlopses: list[str]) -> dict[str, Any]:
    payload = {"answers": build_answers(client, vlopses)}
    response = client.post("/api/transform", params={"vlopse": vlopses}, json=payload)
    response.raise_for_status()
    return response.json()


def mapping_errors(transform_body: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for platform in transform_body.get("by_vlopse", []):
        for answer in platform.get("answers", []):
            if answer.get("type") == "mapping_error":
                errors.append(
                    f"{platform['name']}/{answer.get('question_id')}: "
                    f"{answer.get('description')}"
                )
    return errors
