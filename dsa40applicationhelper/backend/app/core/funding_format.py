"""Format structured funding answers for platform export."""

from __future__ import annotations

import json
from typing import Any

AnswerMap = dict[str, str | None]

_GOOGLE_SPONSOR_TYPE_ALIASES: dict[str, str] = {
    "Self-funded (by your organization)": "Self-funded (i.e., by your organization)",
    "Government agencies": "Government agencies",
    "Private sector organizations": "Private sector organizations",
    "Academic or research institutions": "Other third parties (besides your own organization)",
    "Non-profit or philanthropic entities": "Other third parties (besides your own organization)",
    "Other third parties": "Other third parties (besides your own organization)",
}

_SELF_FUNDED_TYPES = frozenset(
    {
        "Self-funded (by your organization)",
        "Self-funded (i.e., by your organization)",
    }
)


def _parse_json_list(raw: str | None) -> list[dict[str, Any]]:
    if not raw or not str(raw).strip():
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def funding_received(answer_map: AnswerMap) -> str:
    return str(answer_map.get("funding-received") or "").strip()


def funding_entries(answer_map: AnswerMap) -> list[dict[str, Any]]:
    return _parse_json_list(answer_map.get("funding-entries"))


def funding_sources_fallback(answer_map: AnswerMap) -> str:
    return str(answer_map.get("funding-sources") or "").strip()


def _entry_field(entry: dict[str, Any], field_id: str) -> str:
    return str(entry.get(field_id) or "").strip()


def format_funding_entry(entry: dict[str, Any], *, include_percentage: bool = False) -> str:
    name = _entry_field(entry, "funding-source-name")
    source_type = _entry_field(entry, "funding-source-type")
    amount = _entry_field(entry, "funding-amount")
    grant_year = _entry_field(entry, "funding-grant-year")
    duration = _entry_field(entry, "funding-duration")
    percentage = _entry_field(entry, "funding-percentage")
    terms = _entry_field(entry, "funding-terms")
    notes = _entry_field(entry, "funding-notes")

    header_parts: list[str] = []
    if name:
        header_parts.append(name)
    if source_type:
        header_parts.append(source_type)
    lines = [" — ".join(header_parts)] if header_parts else []

    detail_parts: list[str] = []
    if amount:
        detail_parts.append(f"Amount: {amount}")
    if grant_year:
        detail_parts.append(f"Grant year: {grant_year}")
    if duration:
        detail_parts.append(f"Duration: {duration}")
    if include_percentage and percentage:
        detail_parts.append(f"Approximate share: {percentage}")
    if detail_parts:
        lines.append("; ".join(detail_parts))
    if terms:
        lines.append(f"Terms: {terms}")
    if notes:
        lines.append(f"Notes: {notes}")
    return "\n".join(line for line in lines if line.strip())


def _require_funding_details(answer_map: AnswerMap) -> str:
    entries = funding_entries(answer_map)
    if entries:
        blocks = [format_funding_entry(entry) for entry in entries]
        text = "\n\n".join(block for block in blocks if block.strip())
        if text:
            return text
    fallback = funding_sources_fallback(answer_map)
    if fallback:
        return fallback
    raise ValueError(
        "Funding details are required when research funding was received"
    )


def format_funding_summary(answer_map: AnswerMap) -> str:
    received = funding_received(answer_map).lower()
    if received == "no":
        return "No funding received for this research."
    if received != "yes":
        raise ValueError(f"Expected Yes or No for funding-received, got: {received!r}")
    return _require_funding_details(answer_map)


def format_apple_funding_disclosure(answer_map: AnswerMap) -> str:
    """Apple A17: sources, amounts, and terms."""
    received = funding_received(answer_map).lower()
    if received == "no":
        return (
            "No direct or indirect funding, grants, bursaries, commissions, "
            "contingency fees, or other payments are provided in connection "
            "with this research."
        )
    if received != "yes":
        raise ValueError(f"Expected Yes or No for funding-received, got: {received!r}")
    return _require_funding_details(answer_map)


def format_apple_funding_breakdown(answer_map: AnswerMap) -> str:
    """Apple A18: percentage split across funding sources."""
    received = funding_received(answer_map).lower()
    if received == "no":
        return "Not applicable — the research is not funded through a combination of sources."
    if received != "yes":
        raise ValueError(f"Expected Yes or No for funding-received, got: {received!r}")

    entries = funding_entries(answer_map)
    if entries:
        lines: list[str] = []
        for entry in entries:
            name = _entry_field(entry, "funding-source-name") or _entry_field(
                entry, "funding-source-type"
            )
            percentage = _entry_field(entry, "funding-percentage")
            if not name:
                continue
            if percentage:
                lines.append(f"{name}: {percentage}")
            else:
                lines.append(name)
        if lines:
            return "\n".join(lines)

    fallback = funding_sources_fallback(answer_map)
    if fallback:
        return fallback
    raise ValueError(
        "Funding breakdown is required when research funding was received"
    )


def _google_sponsor_type(entry: dict[str, Any]) -> str | None:
    source_type = _entry_field(entry, "funding-source-type")
    if not source_type:
        return None
    return _GOOGLE_SPONSOR_TYPE_ALIASES.get(source_type, source_type)


def format_google_funding_sponsor_types(answer_map: AnswerMap) -> str:
    """Google G23: sponsor institution types."""
    received = funding_received(answer_map).lower()
    if received == "no":
        return "Self-funded (i.e., by your organization)"
    if received != "yes":
        raise ValueError(f"Expected Yes or No for funding-received, got: {received!r}")

    types: list[str] = []
    seen: set[str] = set()
    for entry in funding_entries(answer_map):
        mapped = _google_sponsor_type(entry)
        if mapped and mapped not in seen:
            seen.add(mapped)
            types.append(mapped)

    if not types:
        fallback = funding_sources_fallback(answer_map)
        if fallback:
            return fallback
        raise ValueError("Funding sponsor types are required when funding was received")
    return ", ".join(types)


def format_google_funding_org_names(answer_map: AnswerMap) -> str:
    """Google G24: names of sponsoring organisations (non-self-funded)."""
    received = funding_received(answer_map).lower()
    if received == "no":
        return ""
    if received != "yes":
        raise ValueError(f"Expected Yes or No for funding-received, got: {received!r}")

    names: list[str] = []
    seen: set[str] = set()
    for entry in funding_entries(answer_map):
        source_type = _entry_field(entry, "funding-source-type")
        if source_type in _SELF_FUNDED_TYPES:
            continue
        name = _entry_field(entry, "funding-source-name")
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    if names:
        return ", ".join(names)
    return ""


def format_funding_sources_text(answer_map: AnswerMap) -> str:
    """Free-text funding-sources when funded; fixed phrase when not."""
    received = funding_received(answer_map).lower()
    if received == "no":
        return "no sources of funding"
    if received != "yes":
        raise ValueError(f"Expected Yes or No for funding-received, got: {received!r}")
    text = funding_sources_fallback(answer_map)
    if not text:
        raise ValueError(
            "funding-sources text is required when research funding was received"
        )
    return text


def format_commercial_independence_and(answer_map: AnswerMap) -> str:
    """Yes only when person, organisation, and research are all independent."""
    required = (
        "person-commercial-purpose",
        "org-commercial-purpose",
        "research-commercial-purpose",
    )
    for field_id in required:
        if str(answer_map.get(field_id) or "").strip().lower() != "yes":
            return "No"
    return "Yes"


def format_google_funding_disclosure(answer_map: AnswerMap) -> str:
    """Google G27: name, grant year, duration, and amount per source."""
    received = funding_received(answer_map).lower()
    if received == "no":
        return "No external funding received for this research project."
    if received != "yes":
        raise ValueError(f"Expected Yes or No for funding-received, got: {received!r}")
    return _require_funding_details(answer_map)
