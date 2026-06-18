"""Resolve shared organisations and format team researcher answers."""

from __future__ import annotations

import json
from typing import Any

from app.core.structured_schemas import ORG_FIELD_IDS, PRIMARY_ORG_REF

AnswerMap = dict[str, str | None]


def _parse_json_list(raw: str | None) -> list[dict[str, Any]]:
    if not raw or not str(raw).strip():
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def primary_org_from_flat(answer_map: AnswerMap) -> dict[str, str]:
    return {
        field_id: str(answer_map.get(field_id) or "").strip()
        for field_id in ORG_FIELD_IDS
    }


def resolve_organisation(
    org_id: str,
    answer_map: AnswerMap,
    team_orgs: list[dict[str, Any]],
) -> dict[str, str]:
    org_id = org_id.strip()
    if org_id == PRIMARY_ORG_REF:
        return primary_org_from_flat(answer_map)
    for item in team_orgs:
        if str(item.get("id", "")).strip() == org_id:
            return {
                field_id: _org_item_value(item, field_id) for field_id in ORG_FIELD_IDS
            }
    return {}


def _org_item_value(item: dict[str, Any], field_id: str) -> str:
    if field_id == "org-type":
        return str(item.get("org-type") or item.get("affiliation-type") or "").strip()
    if field_id == "org-commercial-purpose":
        return str(
            item.get("org-commercial-purpose") or item.get("commercial-purpose") or ""
        ).strip()
    return str(item.get(field_id) or "").strip()


def org_display_name(org: dict[str, str]) -> str:
    return org.get("org-name", "").strip() or "Unknown organisation"


def person_display_name(person: dict[str, Any]) -> str:
    first = str(person.get("first-name") or "").strip()
    last = str(person.get("last-name") or "").strip()
    return " ".join(part for part in (first, last) if part).strip() or "Unnamed researcher"


def format_affiliation_line(aff: dict[str, Any], org: dict[str, str]) -> str:
    parts = [org_display_name(org)]
    role = str(aff.get("org-role") or "").strip()
    dept = str(aff.get("org-department") or "").strip()
    if role:
        parts.append(role)
    if dept:
        parts.append(dept)
    line = " — ".join(parts) if len(parts) > 1 else parts[0]
    org_notes: list[str] = []
    for field_id, label in (
        ("org-commercial-purpose", "Independent from commercial interests"),
    ):
        value = org.get(field_id, "").strip()
        if value:
            org_notes.append(f"{label}: {value}")
    if org_notes:
        line = f"{line} ({'; '.join(org_notes)})"
    evidence = str(aff.get("org-evidence") or "").strip()
    if evidence:
        line = f"{line} [evidence: {evidence}]"
    return line


def format_team_researcher_entry(
    member: dict[str, Any],
    answer_map: AnswerMap,
    team_orgs: list[dict[str, Any]],
) -> str:
    person = member.get("person") or {}
    name = person_display_name(person)
    email = str(person.get("email-inst") or "").strip()
    person_commercial = str(
        person.get("person-commercial-purpose") or person.get("commercial-purpose") or ""
    ).strip()
    affiliations = member.get("affiliations") or []
    aff_lines: list[str] = []
    for aff in affiliations:
        if not isinstance(aff, dict):
            continue
        org_id = str(aff.get("organisation_id") or "").strip()
        org = resolve_organisation(org_id, answer_map, team_orgs)
        aff_lines.append(format_affiliation_line(aff, org))
    lines = [name]
    if email:
        lines.append(email)
    if person_commercial:
        lines.append(f"Independent from commercial interests: {person_commercial}")
    if aff_lines:
        lines.append("; ".join(aff_lines))
    return "\n".join(lines)


def format_principal_researcher_collab_line(answer_map: AnswerMap) -> str:
    """Single-line collaborator summary from primary applicant fields."""
    first = str(answer_map.get("first-name") or "").strip()
    last = str(answer_map.get("last-name") or "").strip()
    name = " ".join(part for part in (first, last) if part).strip()
    org = str(answer_map.get("org-name") or "").strip()
    role = str(answer_map.get("org-role") or "").strip()
    parts = [part for part in (name, org, role) if part]
    return ", ".join(parts) if parts else name or org


def resolve_collab_list(answer_map: AnswerMap) -> str | None:
    """Derive basic-platform collab-list from structured team data or primary applicant."""
    if str(answer_map.get("collab-list") or "").strip():
        return None

    researchers = str(answer_map.get("collab-researchers") or "").strip()
    if researchers and researchers != "[]":
        return format_team_researchers(researchers, answer_map)

    collab_binary = str(answer_map.get("collab-binary") or "").strip().lower()
    if collab_binary in {"no", "false", "0"}:
        return "None"
    if collab_binary == "yes":
        principal = format_principal_researcher_collab_line(answer_map)
        return principal or "None"
    return None


def format_team_researchers(
    collab_researchers_raw: str,
    answer_map: AnswerMap,
) -> str:
    members = _parse_json_list(collab_researchers_raw)
    team_orgs = _parse_json_list(answer_map.get("team-organisations"))
    blocks = [
        format_team_researcher_entry(member, answer_map, team_orgs)
        for member in members
        if isinstance(member, dict)
    ]
    return "\n\n".join(block for block in blocks if block.strip())


def format_collab_emails(
    collab_researchers_raw: str,
    answer_map: AnswerMap,
) -> str:
    """Comma-separated collaborator emails for Meta M27."""
    collab_binary = str(answer_map.get("collab-binary") or "").strip().lower()
    if collab_binary != "yes":
        return ""
    members = _parse_json_list(collab_researchers_raw)
    emails: list[str] = []
    for member in members:
        if not isinstance(member, dict):
            continue
        person = member.get("person") or {}
        email = str(
            person.get("email-inst") or person.get("email") or ""
        ).strip()
        if email:
            emails.append(email)
    return ", ".join(emails)


_META_MCL_WEB = "MCL (web-based tool)"
_META_MCL_API = "MCL API (via secure computing platform)"


def format_meta_mcl_research_tools(
    answer_map: AnswerMap,
    *,
    vlopse: str = "meta",
) -> str:
    """Meta M23: web tool always included; API option appended when selected."""
    from app.core.platform_specific import scoped_answer_id

    tools = [_META_MCL_WEB]
    api_flag = str(
        answer_map.get(scoped_answer_id("meta-mcl-api-binary", vlopse)) or ""
    ).strip().lower()
    if api_flag == "yes":
        tools.append(_META_MCL_API)
    return ", ".join(tools)


_ADDR_FIELD_IDS = (
    "org-addr-street",
    "org-addr-city",
    "org-addr-postcode",
    "org-addr-state",
    "org-addr-country",
)


def format_apple_affiliation_demonstration(answer_map: AnswerMap) -> str:
    """Format primary organisation + affiliation for Apple A5."""
    org = primary_org_from_flat(answer_map)
    org_name = org.get("org-name", "").strip()
    if not org_name:
        raise ValueError("Organisation name is required")

    role = str(answer_map.get("org-role") or "").strip()
    department = str(answer_map.get("org-department") or "").strip()
    evidence = str(answer_map.get("org-evidence") or "").strip()
    profile_inst = str(answer_map.get("profile-inst") or "").strip()

    paragraphs: list[str] = []

    affiliation_bits = [part for part in (role, department) if part]
    if affiliation_bits:
        paragraphs.append(f"{org_name}\n{' — '.join(affiliation_bits)}")
    else:
        paragraphs.append(org_name)

    org_type = org.get("org-type", "").strip()
    if org_type:
        paragraphs.append(f"Type: {org_type}")

    address = ", ".join(
        org.get(field_id, "").strip()
        for field_id in _ADDR_FIELD_IDS
        if org.get(field_id, "").strip()
    )
    if address:
        paragraphs.append(address)

    contact_lines: list[str] = []
    if org.get("org-phone", "").strip():
        contact_lines.append(f"Phone: {org['org-phone'].strip()}")
    if org.get("org-website", "").strip():
        contact_lines.append(f"Website: {org['org-website'].strip()}")
    if org.get("org-id", "").strip():
        contact_lines.append(f"Registration number: {org['org-id'].strip()}")
    if contact_lines:
        paragraphs.append("\n".join(contact_lines))

    if profile_inst:
        paragraphs.append(f"Institutional profile: {profile_inst}")

    if evidence:
        paragraphs.append(f"Affiliation evidence: {evidence}")

    return "\n\n".join(paragraphs)
