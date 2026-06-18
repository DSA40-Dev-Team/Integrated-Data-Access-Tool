"""Canonical profile schemas and composite form sections.

Field semantics (intentional separation):
- ``research-ethics`` (research-project-profile): ethics approval documentation for *this* project.
"""

from __future__ import annotations

# Composite question id → schema file stem
COMPOSITE_QUESTIONS: dict[str, str] = {
    "primary-person": "person-profile",
    "primary-organisation": "organisation-profile",
    "primary-affiliation": "primary-affiliation-profile",
    "research-project": "research-project-profile",
    "data-request": "data-request-profile",
    "security-tom": "security-tom-profile",
    "funding": "funding-profile",
    "collaboration": "collaboration-profile",
}

# Repeatable structured sections (not composites)
REPEATABLE_QUESTIONS: dict[str, str] = {
    "team-organisations": "organisation-profile",
    "collab-researchers": "team-member",
    "funding-entries": "funding-entry-profile",
}

# General question ids owned by a profile schema (hidden when composite is shown).
SCHEMA_FIELD_OWNERS: dict[str, tuple[str, ...]] = {
    "person-profile": (
        "first-name",
        "last-name",
        "pref-name",
        "email-inst",
        "researcher-addr-city",
        "researcher-addr-state",
        "researcher-addr-country",
        "profile-inst",
        "profile-platform",
        "orcid",
        "cv",
        "discipline-expertise",
        "prev-experience",
        "prev-experience-detail",
        "person-commercial-purpose",
    ),
    "organisation-profile": (
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
    ),
    "primary-affiliation-profile": (
        "org-role",
        "org-department",
        "org-evidence",
    ),
    "affiliation-profile": (
        "org-role",
        "org-department",
        "org-evidence",
    ),
    "research-project-profile": (
        "research-title",
        "research-summary",
        "research-summary-litreview",
        "research-sysrisk-categories",
        "research-sysrisk",
        "research-keywords",
        "research-method",
        "research-question",
        "research-outcomes",
        "research-citations",
        "research-start",
        "research-end",
        "research-timeline",
        "research-publication-bin",
        "research-publication",
        "research-ethics",
        "research-ethics-irb-us",
        "research-ethics-irb-eea",
        "research-docs",
        "research-commercial-purpose",
    ),
    "data-request-profile": (
        "data-requested",
        "data-requested-U18",
        "data-geoscope",
        "data-timescope-start",
        "data-timescope-end",
        "data-expl",
        "data-acc-start",
        "data-acc-end",
        "data-accmod",
        "data-refresh",
    ),
    "security-tom-profile": (
        "security-capable-binary",
        "security-capable-evidence",
        "tom-technical",
        "tom-organisational",
        "tom-responsible",
        "tom-storagelocation",
        "tom-storage-start",
        "tom-storage-end",
        "purpose-limitation-binary",
        "tom-evidence",
    ),
    "funding-profile": (
        "funding-received",
        "funding-sources",
        "funding-evidence",
    ),
    "collaboration-profile": (
        "collab-binary",
        "collab-list",
        "collab-lead",
        "collab-lead-firstname",
        "collab-lead-lastname",
        "collab-share-binary",
        "collab-share",
    ),
}

# Flat ids never promoted to composite sections
ALWAYS_STANDALONE_IDS = frozenset(
    {
        "legal-dsa",
        "legal-consent",
        "legal-agreement",
        "legal-authority-name",
        "legal-authority-title",
        "legal-authority-email",
        "legal-docs",
        "more-docs",
        "tech-preference",
        "tech-training",
        "tech-client",
        "tech-client-scrape-method",
        "tech-client-ip-type",
        "tech-client-ip",
        "tech-client-token",
        "meta-mcl-api-binary",
        "meta-secure-platform",
    }
)

PLATFORM_SPECIFIC_IN_PERSON = frozenset(
    {"profile-platform", "prev-experience", "prev-experience-detail"}
)

# Mapped fields stay as standalone questions (no composite section in the form).
COMPOSITES_STANDALONE_ONLY: frozenset[str] = frozenset()

# Composite schema fields always shown when the section applies (gate / trigger fields).
COMPOSITE_GATE_FIELDS: dict[str, frozenset[str]] = {
    "funding-profile": frozenset({"funding-received"}),
    "collaboration-profile": frozenset({"collab-binary", "collab-share-binary"}),
    "research-project-profile": frozenset({"research-publication-bin"}),
    "security-tom-profile": frozenset(
        {"security-capable-binary", "purpose-limitation-binary"}
    ),
}


def field_owner_schema(field_id: str) -> str | None:
    base = field_id.split("__", 1)[0]
    for schema, fields in SCHEMA_FIELD_OWNERS.items():
        if base in fields:
            return schema
    return None


def composites_for_mapped_fields(mapped_general_ids: set[str]) -> list[str]:
    from app.core.conditions_util import collab_structured_required

    needed: list[str] = []
    bases = {gid.split("__", 1)[0] for gid in mapped_general_ids}
    for composite_id, schema in COMPOSITE_QUESTIONS.items():
        if composite_id in COMPOSITES_STANDALONE_ONLY:
            continue
        if composite_id == "collaboration" and collab_structured_required(bases):
            continue
        owned = set(SCHEMA_FIELD_OWNERS.get(schema, ()))
        if bases & owned:
            needed.append(composite_id)
    return needed


def composite_owner_for_field(field_id: str) -> str | None:
    base = field_id.split("__", 1)[0]
    for composite_id, schema in COMPOSITE_QUESTIONS.items():
        if base in SCHEMA_FIELD_OWNERS.get(schema, ()):
            return composite_id
    return None


def embedded_field_ids() -> frozenset[str]:
    embedded: set[str] = set()
    for composite_id, schema in COMPOSITE_QUESTIONS.items():
        embedded.update(SCHEMA_FIELD_OWNERS.get(schema, ()))
    return frozenset(embedded)


def composite_field_map() -> dict[str, tuple[str, ...]]:
    return {
        composite_id: SCHEMA_FIELD_OWNERS[schema]
        for composite_id, schema in COMPOSITE_QUESTIONS.items()
    }
