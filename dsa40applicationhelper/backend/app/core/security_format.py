"""Format granular data-security answers for platform export."""

from __future__ import annotations

import json
from typing import Any

AnswerMap = dict[str, str | None]


def _field(answer_map: AnswerMap, field_id: str) -> str:
    return str(answer_map.get(field_id) or "").strip()


def _paragraphs(*parts: str) -> str:
    return "\n\n".join(part for part in parts if part.strip())


def _purpose_limitation_detail(answer_map: AnswerMap) -> str:
    return _field(answer_map, "tom-purposelimit")


def _require_tom_narrative(answer_map: AnswerMap) -> str:
    technical = _field(answer_map, "tom-technical")
    organisational = _field(answer_map, "tom-organisational")
    if not technical and not organisational:
        raise ValueError(
            "Technical or organisational data protection measures are required"
        )
    return _paragraphs(technical, organisational)


def format_tom_summary(answer_map: AnswerMap) -> str:
    """Simple platforms: combined TOM narrative."""
    return _require_tom_narrative(answer_map)


def format_google_data_protection(answer_map: AnswerMap) -> str:
    """Google G32: policies, confidentiality, storage, and breach handling."""
    sections: list[str] = []

    tom = _require_tom_narrative(answer_map)
    sections.append(tom)

    responsible = _field(answer_map, "tom-responsible")
    if responsible:
        sections.append(f"GDPR compliance responsibility: {responsible}")

    location = _field(answer_map, "tom-storagelocation")
    storage_start = _field(answer_map, "tom-storage-start")
    storage_end = _field(answer_map, "tom-storage-end")
    storage_bits = [bit for bit in (location, storage_start, storage_end) if bit]
    if storage_bits:
        sections.append(
            "Storage and protection: " + "; ".join(storage_bits)
        )

    capable = _field(answer_map, "security-capable-binary")
    if capable:
        sections.append(
            f"Organisation capable of fulfilling data security requirements: {capable}"
        )

    return _paragraphs(*sections)


def format_apple_rights_protection(answer_map: AnswerMap) -> str:
    """Apple A13: rights, legitimate interests, and personal data protection."""
    sections: list[str] = []

    technical = _field(answer_map, "tom-technical")
    organisational = _field(answer_map, "tom-organisational")
    if technical or organisational:
        sections.append(
            _paragraphs(
                "Technical and organisational measures:",
                technical,
                organisational,
            )
        )

    responsible = _field(answer_map, "tom-responsible")
    if responsible:
        sections.append(f"Personal data protection / GDPR lead: {responsible}")

    research_ethics = _field(answer_map, "research-ethics")
    if research_ethics:
        sections.append(f"Ethics approval for this project: {research_ethics}")

    data_expl = _field(answer_map, "data-expl")
    if data_expl:
        sections.append(
            "Proportionality and necessity of requested data: " + data_expl
        )

    if not sections:
        raise ValueError(
            "Rights and data protection information is required for Apple A13"
        )
    return _paragraphs(*sections)


def format_apple_purpose_confirmation(answer_map: AnswerMap) -> str:
    """Apple A14: confirmation of no other intended data use."""
    value = _field(answer_map, "purpose-limitation-binary").lower()
    title = _field(answer_map, "research-title")
    scope = f' ("{title}")' if title else ""

    if value == "yes":
        return (
            "I confirm that there is no other intended use of the requested data "
            f"outside of the research described in this application{scope}."
        )
    if value == "no":
        detail = _purpose_limitation_detail(answer_map)
        if detail:
            return (
                "The requested data may also be used outside the primary research "
                f"scope. Intended uses and safeguards: {detail}"
            )
        raise ValueError(
            "Explain other intended uses or confirm sole research use (Yes)"
        )
    raise ValueError(
        f"Expected Yes or No for purpose-limitation-binary, got: {value!r}"
    )


def _format_access_section(answer_map: AnswerMap) -> str:
    lines: list[str] = []
    collab_binary = _field(answer_map, "collab-binary")
    collab_list = _field(answer_map, "collab-list")
    collab_researchers = _field(answer_map, "collab-researchers")

    if collab_binary == "Yes":
        lines.append("Additional persons afforded access: Yes")
        if collab_list:
            lines.append(collab_list)
        if collab_researchers:
            try:
                from app.core.team_research import format_team_researchers

                formatted = format_team_researchers(collab_researchers, answer_map)
                if formatted:
                    lines.append(formatted)
            except (ValueError, TypeError):
                lines.append(collab_researchers)
    elif collab_binary == "No":
        lines.append(
            "Access limited to the applicant and roles described in organisational measures."
        )

    share_binary = _field(answer_map, "collab-share-binary")
    share = _field(answer_map, "collab-share")
    if share_binary == "Yes" and share:
        lines.append(f"Data sharing / combination with third parties: {share}")
    elif share_binary == "No":
        lines.append(
            "The requested data will not be combined with third-party datasets "
            "outside this research."
        )

    return "\n\n".join(lines)


def format_apple_security_arrangements(answer_map: AnswerMap) -> str:
    """Apple A19: TOM arrangements, access, storage, and data combination."""
    sections: list[str] = [_require_tom_narrative(answer_map)]

    responsible = _field(answer_map, "tom-responsible")
    if responsible:
        sections.append(f"Persons responsible for compliance: {responsible}")

    location = _field(answer_map, "tom-storagelocation")
    if location:
        sections.append(f"Data storage location: {location}")

    storage_start = _field(answer_map, "tom-storage-start")
    storage_end = _field(answer_map, "tom-storage-end")
    if storage_start or storage_end:
        sections.append(
            "Planned data retention: "
            + " to ".join(bit for bit in (storage_start, storage_end) if bit)
        )

    access = _format_access_section(answer_map)
    if access:
        sections.append(access)

    return _paragraphs(*sections)


def format_apple_purpose_limitation(answer_map: AnswerMap) -> str:
    """Apple A22: how sole-use for this research will be ensured."""
    binary = _field(answer_map, "purpose-limitation-binary").lower()
    detail = _purpose_limitation_detail(answer_map)
    organisational = _field(answer_map, "tom-organisational")
    responsible = _field(answer_map, "tom-responsible")
    title = _field(answer_map, "research-title")
    summary = _field(answer_map, "research-summary")

    sections: list[str] = []
    if title or summary:
        research_scope = title or "this research"
        if title and summary:
            sections.append(f"Research scope: {title}\n{summary}")
        else:
            sections.append(f"Research scope: {research_scope}")

    if detail:
        sections.append(f"Purpose limitation controls: {detail}")
    elif organisational:
        sections.append(
            "Purpose limitation controls (organisational measures): "
            + organisational
        )
    elif binary == "yes":
        raise ValueError(
            "Organisational measures are required for Apple A22"
        )
    else:
        raise ValueError(
            "Purpose limitation detail or organisational controls are required"
        )

    if responsible:
        sections.append(f"Compliance oversight: {responsible}")

    return _paragraphs(*sections)


def format_pinterest_purpose_gate(answer_map: AnswerMap) -> str:
    """Pinterest P18: sole use for Art. 34(1) research."""
    value = _field(answer_map, "purpose-limitation-binary").lower()
    if value == "yes":
        return (
            "Yes — the requested data will be used solely to perform research "
            "that contributes to detecting, identifying, and understanding "
            "systemic risks in the European Union (Article 34(1) DSA)."
        )
    if value == "no":
        detail = _purpose_limitation_detail(answer_map)
        if detail:
            return (
                "No — other uses are planned. Details: " + detail
            )
        raise ValueError(
            "Explain planned non-research uses or confirm sole research use (Yes)"
        )
    raise ValueError(
        f"Expected Yes or No for purpose-limitation-binary, got: {value!r}"
    )
