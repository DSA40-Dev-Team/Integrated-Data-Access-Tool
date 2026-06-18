import type { DsaQuestion } from "@api/types.gen";
import { COMPOSITE_FIELD_MAP } from "$lib/structured";
import type { ConditionsMap, FormValues } from "$lib/conditions";
import { isAnswerFilled } from "$lib/answerFilled";
import { fieldUnitsForRows, type RequiredContext } from "$lib/formFieldUnits";

export type FormSectionDef = {
  id: string;
  label: string;
};

export const FORM_SECTIONS: FormSectionDef[] = [
  { id: "about-you", label: "About you" },
  { id: "organisation", label: "Organisation" },
  { id: "research", label: "Research project" },
  { id: "data", label: "Data request" },
  { id: "security", label: "Security & TOM" },
  { id: "collaboration", label: "Collaboration" },
  { id: "funding", label: "Funding" },
  { id: "google-tech", label: "Google technical" },
  { id: "meta", label: "Meta" },
  { id: "other", label: "Other" },
];

export type FormRow =
  | { kind: "single"; question: DsaQuestion }
  | {
      kind: "platform_group";
      baseId: string;
      label: string;
      required: boolean;
      variants: DsaQuestion[];
    };

const COMPOSITE_SECTION: Record<string, string> = {
  "primary-person": "about-you",
  "primary-organisation": "organisation",
  "primary-affiliation": "organisation",
  "research-project": "research",
  "data-request": "data",
  "security-tom": "security",
  collaboration: "collaboration",
  funding: "funding",
  "funding-entries": "funding",
  "team-organisations": "collaboration",
  "collab-researchers": "collaboration",
};

function prefixSection(id: string): string | null {
  if (id.startsWith("collab-")) return "collaboration";
  if (id.startsWith("funding-")) return "funding";
  if (id.startsWith("tech-")) return "google-tech";
  if (id.startsWith("meta-")) return "meta";
  if (id.startsWith("research-")) return "research";
  if (id.startsWith("data-")) return "data";
  if (id.startsWith("tom-") || id.startsWith("security-") || id.startsWith("purpose-limitation"))
    return "security";
  return null;
}

export function sectionIdForFieldId(fieldId: string): string {
  const baseId = fieldId.includes("__") ? fieldId.split("__")[0]! : fieldId;
  if (COMPOSITE_SECTION[baseId]) return COMPOSITE_SECTION[baseId];
  for (const [compositeId, fields] of Object.entries(COMPOSITE_FIELD_MAP)) {
    if (fields.includes(baseId)) {
      return COMPOSITE_SECTION[compositeId] ?? prefixSection(baseId) ?? "other";
    }
  }
  return prefixSection(baseId) ?? "other";
}

export function sectionIdForRow(row: FormRow): string {
  if (row.kind === "platform_group") {
    return (
      COMPOSITE_SECTION[row.baseId] ??
      prefixSection(row.baseId) ??
      "other"
    );
  }
  const id = row.question.id;
  return COMPOSITE_SECTION[id] ?? prefixSection(id) ?? "other";
}

export function buildFormRows(questions: DsaQuestion[]): FormRow[] {
  const rows: FormRow[] = [];
  const groupIndex = new Map<string, number>();

  for (const question of questions) {
    const baseId = question.source_general_id;
    if (baseId && question.vlopse) {
      let idx = groupIndex.get(baseId);
      if (idx === undefined) {
        idx = rows.length;
        groupIndex.set(baseId, idx);
        rows.push({
          kind: "platform_group",
          baseId,
          label: question.group_text ?? question.text,
          required: question.required,
          variants: [question],
        });
      } else {
        const row = rows[idx];
        if (row.kind === "platform_group") {
          row.variants.push(question);
          row.required = row.required || question.required;
        }
      }
    } else {
      rows.push({ kind: "single", question });
    }
  }

  return rows;
}

function rowQuestionIds(row: FormRow): string[] {
  if (row.kind === "platform_group") return row.variants.map((variant) => variant.id);
  return [row.question.id];
}

function isRowRequired(question: DsaQuestion, required: RequiredContext): boolean {
  return (
    question.required ||
    required.requiredQuestionIds.has(question.id) ||
    required.requiredFieldIds.has(question.id)
  );
}

export type SectionStats = {
  id: string;
  label: string;
  total: number;
  filled: number;
  requiredTotal: number;
  requiredFilled: number;
  errorCount: number;
};

export function sectionStatsForRows(
  rows: FormRow[],
  visibility: Record<string, boolean>,
  values: FormValues,
  errorIds: Set<string>,
  conditions: ConditionsMap = {},
  required: RequiredContext,
): SectionStats[] {
  const bySection = new Map<string, SectionStats>();

  for (const def of FORM_SECTIONS) {
    bySection.set(def.id, {
      id: def.id,
      label: def.label,
      total: 0,
      filled: 0,
      requiredTotal: 0,
      requiredFilled: 0,
      errorCount: 0,
    });
  }

  for (const row of rows) {
    const sectionId = sectionIdForRow(row);
    const stats = bySection.get(sectionId);
    if (!stats) continue;

    const units = fieldUnitsForRows([row], visibility, values, conditions, required);
    if (units.length === 0) {
      if (row.kind === "single") {
        const question = row.question;
        const visible = visibility[question.id] ?? true;
        if (!visible && !question.required) {
          // Hidden optional row — do not affect section progress.
        } else {
          const filled = isAnswerFilled(values[question.id], question.input_type);
          const rowRequired = isRowRequired(question, required);
          const isStructured =
            question.input_type === "composite_group" ||
            question.input_type === "repeatable_group";

          // Empty optional composites/repeatables (e.g. collaborators removed) are complete.
          if (!(isStructured && !filled && !rowRequired)) {
            stats.total += 1;
            if (filled) stats.filled += 1;
            if (rowRequired) {
              stats.requiredTotal += 1;
              if (filled) stats.requiredFilled += 1;
            }
          }
        }
      }
    } else {
      for (const unit of units) {
        stats.total += 1;
        if (unit.filled) stats.filled += 1;
        if (unit.required) {
          stats.requiredTotal += 1;
          if (unit.filled) stats.requiredFilled += 1;
        }
      }
    }

    for (const questionId of rowQuestionIds(row)) {
      if (errorIds.has(questionId)) stats.errorCount += 1;
    }
  }

  return FORM_SECTIONS.map((def) => bySection.get(def.id)!)
    .filter((stats) => stats.total > 0);
}

export function groupRowsBySection(rows: FormRow[]): { section: FormSectionDef; rows: FormRow[] }[] {
  const grouped = new Map<string, FormRow[]>();
  for (const def of FORM_SECTIONS) grouped.set(def.id, []);

  for (const row of rows) {
    const sectionId = sectionIdForRow(row);
    grouped.get(sectionId)?.push(row);
  }

  return FORM_SECTIONS.map((def) => ({
    section: def,
    rows: grouped.get(def.id) ?? [],
  })).filter((entry) => entry.rows.length > 0);
}
