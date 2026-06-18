export type SchemaField = {
  id: string;
  text_en: string;
  type: string;
  help?: string | null;
  platform_help?: Record<string, string> | null;
  config?: Record<string, unknown> | null;
  options?: string[] | null;
  granularity?: string | null;
  scoped_platforms?: string[] | null;
};

const ANSWER_KEY_SEP = "__";

export type FieldSchema = {
  name: string;
  schema: Record<string, unknown>;
  fields: SchemaField[];
};

export type OrgOption = {
  id: string;
  label: string;
};

export const PRIMARY_ORG_ID = "primary";

/** Composite section id → flat field ids (mirrors backend schema_registry). */
export const COMPOSITE_FIELD_MAP: Record<string, string[]> = {
  "primary-person": [
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
  ],
  "primary-organisation": [
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
  ],
  "primary-affiliation": ["org-role", "org-department", "org-evidence"],
  "research-project": [
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
  ],
  "data-request": [
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
  ],
  "security-tom": [
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
  ],
  funding: ["funding-received", "funding-sources", "funding-evidence"],
  collaboration: [
    "collab-binary",
    "collab-list",
    "collab-lead",
    "collab-lead-firstname",
    "collab-lead-lastname",
    "collab-share-binary",
    "collab-share",
  ],
};

/** Schema name → leaf field ids (mirrors backend `data/schemas/*.json`). */
export const SCHEMA_FIELDS: Record<string, string[]> = {
  "person-profile": COMPOSITE_FIELD_MAP["primary-person"],
  "organisation-profile": COMPOSITE_FIELD_MAP["primary-organisation"],
  "primary-affiliation-profile": COMPOSITE_FIELD_MAP["primary-affiliation"],
  "research-project-profile": COMPOSITE_FIELD_MAP["research-project"],
  "data-request-profile": COMPOSITE_FIELD_MAP["data-request"],
  "security-tom-profile": COMPOSITE_FIELD_MAP["security-tom"],
  "funding-profile": COMPOSITE_FIELD_MAP.funding,
  "collaboration-profile": COMPOSITE_FIELD_MAP.collaboration,
  "affiliation-profile": ["org-role", "org-department", "org-evidence"],
  "funding-entry-profile": [
    "funding-source-name",
    "funding-source-type",
    "funding-amount",
    "funding-grant-year",
    "funding-duration",
    "funding-percentage",
    "funding-terms",
    "funding-notes",
  ],
};

/** Gate fields always shown inside a composite (mirrors backend schema_registry). */
export const COMPOSITE_GATE_FIELDS: Record<string, string[]> = {
  "funding-profile": ["funding-received"],
  "collaboration-profile": ["collab-binary", "collab-share-binary"],
  "research-project-profile": ["research-publication-bin"],
  "security-tom-profile": ["security-capable-binary", "purpose-limitation-binary"],
};

function parseObject(raw: string | undefined): Record<string, unknown> {
  if (!raw?.trim()) return {};
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

/** Flatten composite JSON sections for condition evaluation and transforms. */
export function expandFormValues(
  values: Record<string, string | undefined>,
): Record<string, string | undefined> {
  const out = { ...values };
  for (const [compositeId, fields] of Object.entries(COMPOSITE_FIELD_MAP)) {
    const payload = parseObject(values[compositeId]);
    for (const fieldId of fields) {
      const current = out[fieldId];
      if (current !== undefined && String(current).trim() !== "") continue;
      const v = payload[fieldId];
      if (v === undefined) continue;
      if (isPlatformScopedDict(v)) {
        for (const [platform, scopedVal] of Object.entries(v)) {
          if (scopedVal === undefined || String(scopedVal).trim() === "") continue;
          const key = platform.includes(ANSWER_KEY_SEP)
            ? platform
            : `${fieldId}${ANSWER_KEY_SEP}${platform}`;
          if (!out[key]?.trim()) out[key] = String(scopedVal);
        }
        continue;
      }
      if (String(v).trim() !== "") {
        out[fieldId] = String(v);
      }
    }
  }
  _syncOrgLegacyAliases(out);
  return out;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isPlatformScopedDict(value: unknown): value is Record<string, unknown> {
  if (!isRecord(value)) return false;
  return Object.values(value).every(
    (entry) =>
      entry === null ||
      typeof entry === "string" ||
      typeof entry === "number" ||
      typeof entry === "boolean",
  );
}

function _syncOrgLegacyAliases(out: Record<string, string | undefined>): void {
  const affType = out["affiliation-type"]?.trim() ?? "";
  const orgType = out["org-type"]?.trim() ?? "";
  if (affType && !orgType) out["org-type"] = affType;
}

function fieldPayloadFilled(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "object" && !Array.isArray(value)) {
    return Object.values(value as Record<string, unknown>).some((entry) =>
      fieldPayloadFilled(entry),
    );
  }
  return false;
}

/** Move legacy top-level answers into composite JSON so server-side transform sees them. */
export function migrateFlatFieldsIntoComposites(
  values: Record<string, string | undefined>,
): Record<string, string | undefined> {
  const out = { ...values };
  for (const [compositeId, fields] of Object.entries(COMPOSITE_FIELD_MAP)) {
    const payload = parseObject(out[compositeId]);
    let changed = false;

    for (const fieldId of fields) {
      const flat = out[fieldId]?.trim();
      if (flat && !fieldPayloadFilled(payload[fieldId])) {
        payload[fieldId] = flat;
        changed = true;
      }

      for (const [key, rawValue] of Object.entries(out)) {
        if (!key.startsWith(`${fieldId}${ANSWER_KEY_SEP}`)) continue;
        const platform = key.slice(fieldId.length + ANSWER_KEY_SEP.length);
        const scoped = rawValue?.trim();
        if (!scoped) continue;
        const existing = payload[fieldId];
        const dict: Record<string, string> = isPlatformScopedDict(existing)
          ? Object.fromEntries(
              Object.entries(existing as Record<string, unknown>).map(([k, v]) => [
                k,
                String(v ?? ""),
              ]),
            )
          : typeof existing === "string" && existing.trim()
            ? { _: existing }
            : {};
        if (!dict[platform]?.trim()) {
          dict[platform] = scoped;
          payload[fieldId] = dict;
          changed = true;
        }
      }
    }

    if (changed) {
      out[compositeId] = JSON.stringify(payload);
    }
  }

  return out;
}

export function parseItems(raw: string): Record<string, unknown>[] {
  if (!raw?.trim()) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function serializeItems(items: Record<string, unknown>[]): string {
  return JSON.stringify(items);
}

export function nextOrgId(items: Record<string, unknown>[]): string {
  const used = new Set(
    items
      .map((item) => String(item.id ?? "").trim())
      .filter((id) => id.startsWith("org-")),
  );
  let n = 1;
  while (used.has(`org-${n}`)) n += 1;
  return `org-${n}`;
}

export function buildOrgOptions(
  teamOrganisationsRaw: string,
  flatValues: Record<string, string | undefined>,
): OrgOption[] {
  const options: OrgOption[] = [
    {
      id: PRIMARY_ORG_ID,
      label: flatValues["org-name"]?.trim()
        ? `My organisation (${flatValues["org-name"].trim()})`
        : "My organisation (from your answers above)",
    },
  ];
  for (const item of parseItems(teamOrganisationsRaw)) {
    const id = String(item.id ?? "").trim();
    const name = String(item["org-name"] ?? "").trim();
    if (id) {
      options.push({ id, label: name || id });
    }
  }
  return options;
}
