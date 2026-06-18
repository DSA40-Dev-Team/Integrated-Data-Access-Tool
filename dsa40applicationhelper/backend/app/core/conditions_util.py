"""Parse platform form conditions and expose them on general question ids.

Visibility is evaluated on **general question answers** in the helper form.
Operations (e.g. apple-collab-sentence) run only at transform/submit time.

When remapping a platform condition clause that references a platform field
mapped *through* an operation, we resolve the clause to the operation's
**input** general id(s) via ``mapping_target`` — never the transformed output.
Example: Apple A3 (collab-binary → apple-collab-sentence); clause ``A3 == Yes``
becomes ``collab-binary == Yes`` in the unified form.
"""

import re
from collections import defaultdict

from app.core.models import Condition, PlatformMapping

COLLAB_TRIGGER_IDS = frozenset({"collab-binary", "collab-list", "collab-researchers"})
COLLAB_STRUCTURED_TRIGGER_IDS = frozenset({"collab-researchers"})
COLLAB_BASIC_FIELD_IDS = frozenset({"collab-list"})
COLLAB_STRUCTURED_SUPPLEMENT_IDS = frozenset({"team-organisations", "collab-researchers"})
# Legacy alias used by form supplements
COLLAB_SUPPLEMENT_GENERAL_IDS = COLLAB_STRUCTURED_SUPPLEMENT_IDS
PUBLICATION_TRIGGER_IDS = frozenset({"research-publication-bin"})
PUBLICATION_SUPPLEMENT_GENERAL_IDS = frozenset({"research-publication"})
FUNDING_TRIGGER_IDS = frozenset({"funding-received", "funding-sources"})
FUNDING_SUPPLEMENT_GENERAL_IDS = frozenset({"funding-entries"})
PURPOSE_LIMITATION_TRIGGER_IDS = frozenset({"purpose-limitation-binary"})
PURPOSE_LIMITATION_SUPPLEMENT_IDS = frozenset({"tom-purposelimit"})
COLLAB_SHARE_TRIGGER_IDS = frozenset({"collab-share-binary"})
COLLAB_SHARE_SUPPLEMENT_IDS = frozenset({"collab-share"})
TECH_CLIENT_TRIGGER_IDS = frozenset(
    {
        "tech-client-visibility",
        "tech-client-multi-project",
        "tech-client-scrape-method",
        "tech-client-ip-type",
    }
)
GOOGLE_TECH_FIELD_IDS = frozenset(
    {
        "tech-client",
        "tech-client-scrape-method",
        "tech-client-ip-type",
        "tech-client-ip",
        "tech-client-token",
    }
)
ORG_AFFILIATION_TRIGGER_IDS = frozenset({"org-name"})
ORG_AFFILIATION_SUPPLEMENT_COMPOSITE_IDS = frozenset({"primary-affiliation"})

_CONDITION_CLAUSE = re.compile(
    r"([A-Z]\d+)\s*==\s*(.+?)(?=\s+(?:AND|&&)\s+[A-Z]\d+\s*==|$)",
    re.IGNORECASE,
)

# CSV condition typos → platform option text (TikTok and shared forms).
_VALUE_ALIASES: dict[str, str] = {
    "Academic Institute": "Academic institution",
    "Student": "Research student",
    "US": "US and its territories",
    "EEA": "EEA (European Economic Area), UK, or Switzerland",
}


def evaluate_condition_on_map(
    clause: Condition, answer_map: dict[str, str | None]
) -> bool:
    """Evaluate a single condition against flat/scoped helper answers."""
    actual = answer_map.get(clause.question_id)
    if clause.operator == "eq":
        return actual == clause.value
    if clause.operator == "neq":
        return actual != clause.value
    return False


def field_visible_in_helper(
    field_id: str,
    conditions: dict[str, list[list[Condition]]],
    answer_map: dict[str, str | None],
) -> bool:
    """True when unified-form visibility rules say the field applies."""
    rules = conditions.get(field_id)
    if not rules:
        return True
    return any(
        all(evaluate_condition_on_map(clause, answer_map) for clause in group)
        for group in rules
    )


def mapping_applicable_for_helper(
    *,
    vlopse: str,
    general_ids: list[str],
    platform_required: bool,
    answer_map: dict[str, str | None],
    merged_conditions: dict[str, list[list[Condition]]],
) -> bool:
    """True when an empty mapping must be attempted; False when it should be skipped."""
    for general_id in general_ids:
        keys = [general_id]
        if vlopse:
            from app.core.platform_specific import scoped_answer_id

            keys.append(scoped_answer_id(general_id, vlopse))
        for key in keys:
            if key in merged_conditions and not field_visible_in_helper(
                key, merged_conditions, answer_map
            ):
                return False
    if not platform_required:
        return False
    return True


def parse_condition_clauses(condition: str) -> list[tuple[str, str]]:
    """Return (platform_question_id, value) pairs from a platform Condition cell."""
    condition = condition.strip()
    if not condition:
        return []
    if condition.lower().startswith("if "):
        condition = condition[3:].strip()
    clauses: list[tuple[str, str]] = []
    for match in _CONDITION_CLAUSE.finditer(condition):
        platform_id, raw_value = match.group(1).upper(), match.group(2).strip()
        value = _VALUE_ALIASES.get(raw_value, raw_value)
        clauses.append((platform_id, value))
    return clauses


def general_ids_from_mapping(entry: PlatformMapping | dict[str, object]) -> list[str]:
    """General input ids for a mapping entry (operation inputs, not derived output)."""
    if isinstance(entry, str):
        return [entry]
    operation: str | None
    src: object
    if isinstance(entry, dict):
        operation = str(entry["operation"]) if entry.get("operation") else None
        src = entry.get("src")
    else:
        operation = entry.operation
        src = entry.src
    if operation:
        from app.core.operator import operation_constant_output

        if operation_constant_output(operation):
            return []
    if isinstance(src, list):
        return [str(s) for s in src]
    if isinstance(src, str):
        return [src]
    return []


def mapping_target(mappings: dict[str, PlatformMapping], platform_id: str) -> str | None:
    """Primary general id for a platform field (first mapping input)."""
    entry = mappings.get(platform_id)
    if entry is None:
        return None
    ids = general_ids_from_mapping(entry)
    return ids[0] if ids else None


def mapped_general_ids(mappings: dict[str, PlatformMapping]) -> set[str]:
    ids: set[str] = set()
    for entry in mappings.values():
        ids.update(general_ids_from_mapping(entry))
    return ids


def collaboration_relevant(mapped_general: set[str]) -> bool:
    return bool(mapped_general & COLLAB_TRIGGER_IDS)


def collab_structured_required(mapped_general: set[str]) -> bool:
    """True when any selected platform maps structured team data (e.g. Apple, Meta)."""
    return bool(mapped_general & COLLAB_STRUCTURED_TRIGGER_IDS)


def collab_supplements_for(mapped_general: set[str]) -> frozenset[str]:
    if collab_structured_required(mapped_general):
        return COLLAB_STRUCTURED_SUPPLEMENT_IDS
    return frozenset()


def publication_relevant(mapped_general: set[str]) -> bool:
    return bool(mapped_general & PUBLICATION_TRIGGER_IDS)


def funding_relevant(mapped_general: set[str]) -> bool:
    return bool(mapped_general & FUNDING_TRIGGER_IDS)


def purpose_limitation_relevant(mapped_general: set[str]) -> bool:
    return bool(mapped_general & PURPOSE_LIMITATION_TRIGGER_IDS)


def collab_share_relevant(mapped_general: set[str]) -> bool:
    return bool(mapped_general & COLLAB_SHARE_TRIGGER_IDS)


def tech_client_relevant(mapped_general: set[str]) -> bool:
    return bool(mapped_general & TECH_CLIENT_TRIGGER_IDS)


def _service_condition(value: str) -> Condition:
    return Condition(question_id="data-accmod", operator="eq", value=value)


def google_tech_client_condition_groups() -> dict[str, list[list[Condition]]]:
    """Service-gated visibility for Google platform-specific technical fields."""
    play = [_service_condition("Play")]
    shopping = [_service_condition("Shopping")]
    youtube = [_service_condition("YouTube")]
    return {
        "tech-client": [[_service_condition("Maps")]],
        "tech-client-scrape-method": [play, shopping],
        "tech-client-ip-type": [play, shopping, youtube],
        "tech-client-ip": [play, shopping, youtube],
        "tech-client-token": [youtube],
    }


def granularity_for_general(general_id: str) -> str:
    from app.services.question_store import load_unified_questions

    base = general_id.split("__", 1)[0]
    for record in load_unified_questions():
        if record.id == base:
            return record.granularity or "general"
    return "general"


def scoped_condition_key(general_id: str, vlopse: str) -> str:
    from app.core.platform_specific import scoped_answer_id

    if granularity_for_general(general_id) == "platform_specific":
        return scoped_answer_id(general_id, vlopse)
    return general_id


def general_condition_triggers(or_groups: list[list[Condition]]) -> set[str]:
    return {clause.question_id for group in or_groups for clause in group}


def covered_general_targets(
    mappings: dict[str, PlatformMapping],
    platform_conditions: dict[str, list[Condition]],
) -> set[str]:
    covered: set[str] = set()
    for platform_qid in platform_conditions:
        entry = mappings.get(platform_qid)
        if entry is None:
            continue
        covered.update(general_ids_from_mapping(entry))
    return covered


def remap_clauses_to_general(
    mappings: dict[str, PlatformMapping],
    clauses: list[Condition],
    *,
    known_general_ids: set[str] | None = None,
) -> list[Condition]:
    """Remap platform clause ids to general ids for display/runtime."""
    known = known_general_ids or set()
    remapped: list[Condition] = []
    for clause in clauses:
        qid = clause.question_id
        if qid in known:
            remapped.append(clause)
            continue
        general = mapping_target(mappings, qid)
        if general:
            remapped.append(
                Condition(
                    question_id=general,
                    operator=clause.operator,
                    value=clause.value,
                )
            )
    return remapped


def remap_clause_to_general(
    mappings: dict[str, PlatformMapping],
    platform_id: str,
    value: str,
) -> Condition | None:
    general_id = mapping_target(mappings, platform_id)
    if general_id is None:
        return None
    return Condition(question_id=general_id, operator="eq", value=value)


def platform_conditions_to_general_groups(
    mappings: dict[str, PlatformMapping],
    platform_conditions: dict[str, list[Condition]],
) -> dict[str, list[list[Condition]]]:
    """Map platform-keyed AND-clauses to general ids; OR multiple clauses per general field."""
    by_general: dict[str, list[list[Condition]]] = defaultdict(list)

    for platform_qid, raw_clauses in platform_conditions.items():
        general_target = mapping_target(mappings, platform_qid)
        if general_target is None:
            general_target = platform_qid
        known_general = mapped_general_ids(mappings)
        group: list[Condition] = []
        for clause in raw_clauses:
            if isinstance(clause, Condition):
                qid, value, op = clause.question_id, clause.value, clause.operator
            else:
                qid = clause["question_id"]
                value = clause["value"]
                op = clause.get("operator", "eq")
            if qid in known_general or mapping_target(mappings, qid) is None:
                remapped = Condition(question_id=qid, operator=op, value=value)
            else:
                base = remap_clause_to_general(mappings, qid, value)
                remapped = (
                    Condition(
                        question_id=base.question_id,
                        operator=op,
                        value=base.value,
                    )
                    if base
                    else None
                )
            if remapped:
                group.append(remapped)
        if group:
            by_general[general_target].append(group)

    return dict(by_general)


def parse_row_condition(
    mappings: dict[str, PlatformMapping], condition: str
) -> list[Condition]:
    """Parse a CSV Condition cell into remapped general Condition objects."""
    group: list[Condition] = []
    for platform_id, value in parse_condition_clauses(condition):
        remapped = remap_clause_to_general(mappings, platform_id, value)
        if remapped:
            group.append(remapped)
    return group


def normalize_stored_conditions(
    raw: dict[str, object] | None,
    *,
    known_general_ids: set[str] | None = None,
) -> dict[str, list[Condition]]:
    """Coerce vlopse JSON conditions into dict[str, list[Condition]].

    Tolerates legacy/corrupt shapes:
    - OR-groups stored as list[list[clause]] (uses the first AND group)
    - clause question_ids that are already general ids
    """
    if not raw:
        return {}
    known = known_general_ids or set()
    out: dict[str, list[Condition]] = {}
    for target_key, raw_group in raw.items():
        if not isinstance(raw_group, list) or not raw_group:
            continue
        and_group: list[object]
        if isinstance(raw_group[0], list):
            and_group = raw_group[0]
        else:
            and_group = raw_group
        clauses: list[Condition] = []
        for item in and_group:
            if not isinstance(item, dict):
                continue
            clause = Condition.model_validate(item)
            if (
                clause.question_id not in known
                and mapping_target({}, clause.question_id) is None
            ):
                # Keep clause; general id passthrough is handled at compile time.
                pass
            clauses.append(clause)
        if clauses:
            out[str(target_key)] = clauses
    return out
