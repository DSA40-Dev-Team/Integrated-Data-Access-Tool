"""Format organisation affiliation answers for platform export."""

from __future__ import annotations

from app.core.team_research import AnswerMap, org_display_name, primary_org_from_flat

_TIKTOK_EU_NFP_ORG_TYPE = (
    "Not-for-profit body, organization or association (based in the EU 27 Member States only)"
)
_TIKTOK_NFP_BODY = "Not-for-profit body"
_TIKTOK_EU_ASSOCIATION = (
    "organization or association (based in the EU 27 Member States only)"
)

_TIKTOK_NFP_ORG_TYPES = frozenset(
    {
        "Non-governmental organization (NGO)",
        "Independent research organization (IRO)",
        "Government agency",
        "Intergovernmental organization (IGO)",
    }
)


def format_tiktok_affiliation_type(answer_map: AnswerMap) -> str:
    """Map shared org-type to TikTok T2 affiliation options."""
    org_type = str(answer_map.get("org-type") or "").strip()
    if org_type == "Academic institution":
        return "Academic institution"
    if org_type == _TIKTOK_EU_NFP_ORG_TYPE:
        return _TIKTOK_EU_ASSOCIATION
    if org_type in _TIKTOK_NFP_ORG_TYPES:
        return _TIKTOK_NFP_BODY
    raise ValueError(
        f"Cannot derive TikTok affiliation category from org-type: {org_type!r}"
    )


def format_org_affiliation_summary(answer_map: AnswerMap) -> str:
    """Organisation affiliation narrative for X X4."""
    org = primary_org_from_flat(answer_map)
    org_name = org_display_name(org)
    if not org_name or org_name == "Unknown organisation":
        raise ValueError("Organisation name is required")

    lines: list[str] = [org_name]
    org_type = org.get("org-type", "").strip()
    if org_type:
        lines.append(f"Type: {org_type}")

    role = str(answer_map.get("org-role") or "").strip()
    department = str(answer_map.get("org-department") or "").strip()
    affiliation_bits = [part for part in (role, department) if part]
    if affiliation_bits:
        lines.append(" — ".join(affiliation_bits))

    website = org.get("org-website", "").strip()
    if website:
        lines.append(f"Website: {website}")

    return "\n".join(lines)


def format_x_commercial_interests(answer_map: AnswerMap) -> str:
    """X X6: organisational independence plus supporting evidence."""
    org = primary_org_from_flat(answer_map)
    lines: list[str] = []

    org_independence = str(answer_map.get("org-commercial-purpose") or "").strip()
    if org_independence:
        lines.append(
            f"Organisation independent from commercial interests: {org_independence}"
        )

    evidence = str(answer_map.get("org-evidence") or "").strip()
    if evidence:
        lines.append(f"Supporting evidence: {evidence}")

    if not lines:
        raise ValueError(
            "Organisational commercial independence or evidence is required for X6"
        )
    return "\n\n".join(lines)
