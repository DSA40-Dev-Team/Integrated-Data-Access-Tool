"""Project structured composite answers onto flat general question ids."""

from __future__ import annotations

import json
from typing import Any

from app.core.models import Answer
from app.core.platform_specific import (
    ANSWER_KEY_SEP,
    is_platform_specific_general,
    platform_specific_general_ids,
    scoped_answer_id,
)
from app.core.schema_registry import (
    COMPOSITE_QUESTIONS,
    composite_field_map,
    composites_for_mapped_fields,
    embedded_field_ids,
)

# Expansion order: person before organisation (org commercial fill gaps).
_COMPOSITE_EXPAND_ORDER: tuple[str, ...] = (
    "primary-person",
    "primary-organisation",
    "primary-affiliation",
    "research-project",
    "data-request",
    "security-tom",
    "funding",
    "collaboration",
)

EMBEDDED_STANDALONE_IDS = embedded_field_ids()
COMPOSITE_FIELD_MAP = composite_field_map()


def _parse_json_object(raw: str | None) -> dict[str, Any]:
    if not raw or not str(raw).strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _project_field(
    expanded: dict[str, str | None],
    field_id: str,
    value: Any,
    *,
    composite_id: str,
    vlopses: list[str] | None = None,
) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        for key, scoped_val in value.items():
            if scoped_val is None or not str(scoped_val).strip():
                continue
            if ANSWER_KEY_SEP in key:
                expanded[key] = str(scoped_val)
            else:
                expanded[scoped_answer_id(field_id, key)] = str(scoped_val)
        return

    if not str(value).strip():
        return
    text = str(value).strip()

    if is_platform_specific_general(field_id):
        if vlopses:
            from app.core.platform_specific import vlopse_maps_to_general

            for vlopse in vlopses:
                if vlopse_maps_to_general(vlopse, field_id):
                    scoped = scoped_answer_id(field_id, vlopse)
                    if not expanded.get(scoped):
                        expanded[scoped] = text
        else:
            expanded[field_id] = text
        return

    current = expanded.get(field_id)
    if current is None or not str(current).strip():
        expanded[field_id] = text


def _lift_legacy_security_fields(
    payload: dict[str, Any],
    expanded: dict[str, str | None],
) -> None:
    legacy = payload.get("tom-purposelimit")
    if legacy is None or not str(legacy).strip():
        return
    if not str(expanded.get("tom-purposelimit") or "").strip():
        expanded["tom-purposelimit"] = str(legacy).strip()


def _lift_legacy_commercial_purpose(
    payload: dict[str, Any],
    composite_id: str,
    expanded: dict[str, str | None],
) -> None:
    """Map legacy composite key commercial-purpose to scoped person/org ids."""
    legacy = payload.get("commercial-purpose")
    if legacy is None or not str(legacy).strip():
        return
    text = str(legacy).strip()
    if composite_id == "primary-person":
        target = "person-commercial-purpose"
    elif composite_id == "primary-organisation":
        target = "org-commercial-purpose"
    else:
        return
    if not str(expanded.get(target) or "").strip():
        expanded[target] = text


def _sync_legacy_commercial_purpose_alias(expanded: dict[str, str | None]) -> None:
    """Flat commercial-purpose for vlopse mappings that predate the person/org split."""
    if str(expanded.get("commercial-purpose") or "").strip():
        return
    person = str(expanded.get("person-commercial-purpose") or "").strip()
    org = str(expanded.get("org-commercial-purpose") or "").strip()
    if person:
        expanded["commercial-purpose"] = person
    elif org:
        expanded["commercial-purpose"] = org


def expand_primary_answer_map(
    answer_map: dict[str, str | None],
    *,
    vlopses: list[str] | None = None,
) -> dict[str, str | None]:
    """Fill flat general ids from composite JSON when standalone values are absent."""
    expanded = dict(answer_map)

    for composite_id in _COMPOSITE_EXPAND_ORDER:
        if composite_id not in COMPOSITE_FIELD_MAP:
            continue
        payload = _parse_json_object(answer_map.get(composite_id))
        _lift_legacy_commercial_purpose(payload, composite_id, expanded)
        if composite_id == "security-tom":
            _lift_legacy_security_fields(payload, expanded)
        for field_id in COMPOSITE_FIELD_MAP[composite_id]:
            _project_field(
                expanded,
                field_id,
                payload.get(field_id),
                composite_id=composite_id,
                vlopses=vlopses,
            )

    # Legacy single-string platform-specific values → scoped keys
    if vlopses:
        from app.core.platform_specific import vlopse_maps_to_general

        for field_id in platform_specific_general_ids():
            raw = expanded.get(field_id)
            if raw is None or not str(raw).strip() or ANSWER_KEY_SEP in str(raw):
                continue
            text = str(raw).strip()
            for vlopse in vlopses:
                if vlopse_maps_to_general(vlopse, field_id):
                    scoped = scoped_answer_id(field_id, vlopse)
                    if not expanded.get(scoped):
                        expanded[scoped] = text

    _lift_legacy_org_composite_fields(answer_map, expanded)
    _sync_org_legacy_aliases(expanded)
    _sync_legacy_commercial_purpose_alias(expanded)
    _sync_collab_list_from_structured(expanded)
    _sync_email_aliases(expanded)
    return expanded


def _sync_email_aliases(expanded: dict[str, str | None]) -> None:
    """Migrate legacy ``email`` answers into ``email-inst``."""
    email = str(expanded.get("email") or "").strip()
    inst = str(expanded.get("email-inst") or "").strip()
    if email and not inst:
        expanded["email-inst"] = email


def _sync_collab_list_from_structured(expanded: dict[str, str | None]) -> None:
    """Project structured team answers into collab-list for basic platform exports."""
    from app.core.team_research import resolve_collab_list

    derived = resolve_collab_list(expanded)
    if derived is not None:
        expanded["collab-list"] = derived


def _lift_legacy_org_composite_fields(
    answer_map: dict[str, str | None],
    expanded: dict[str, str | None],
) -> None:
    """Read affiliation-type from stored organisation JSON into org-type."""
    payload = _parse_json_object(answer_map.get("primary-organisation"))
    aff = str(payload.get("affiliation-type") or "").strip()
    if aff and not str(expanded.get("org-type") or "").strip():
        expanded["org-type"] = aff


def _sync_org_legacy_aliases(expanded: dict[str, str | None]) -> None:
    """Legacy field ids folded into org-type."""
    aff_type = str(expanded.get("affiliation-type") or "").strip()
    org_type = str(expanded.get("org-type") or "").strip()
    if aff_type and not org_type:
        expanded["org-type"] = aff_type


def expand_answers(
    answers: list[Answer],
    *,
    vlopses: list[str] | None = None,
) -> list[Answer]:
    """Return answers augmented with projected flat ids for transform/mapping."""
    value_map = {a.question_id: a.value for a in answers}
    expanded_map = expand_primary_answer_map(value_map, vlopses=vlopses)
    by_id = {a.question_id: a for a in answers}
    result = list(answers)
    for field_id, value in expanded_map.items():
        if field_id in by_id:
            continue
        if value is None or not str(value).strip():
            continue
        result.append(Answer(question_id=field_id, value=value))
    return result


def is_embedded_field(general_id: str) -> bool:
    base = general_id.split(ANSWER_KEY_SEP, 1)[0]
    return base in EMBEDDED_STANDALONE_IDS
