import type { FormValues } from "$lib/conditions";
import {
  buildRequiredContext,
  fieldUnitsForRows,
  type RequiredContext,
} from "$lib/formFieldUnits";
import { sectionIdForFieldId, type FormRow } from "$lib/formSections";
import type { ConditionsMap } from "$lib/conditions";
import type { DsaQuestion } from "@api/types.gen";

export type MissingField = {
  questionId: string;
  label: string;
  sectionId: string;
};

export type ReadinessReport = {
  ready: boolean;
  missing: MissingField[];
  missingBySection: Record<string, number>;
};

export function computeReadiness(
  rows: FormRow[],
  visibility: Record<string, boolean>,
  values: FormValues,
  conditions: ConditionsMap,
  required: RequiredContext,
): ReadinessReport {
  const missing: MissingField[] = [];
  const seen = new Set<string>();

  for (const unit of fieldUnitsForRows(rows, visibility, values, conditions, required)) {
    if (!unit.required || unit.filled) continue;
    if (seen.has(unit.fieldId)) continue;
    seen.add(unit.fieldId);
    const scrollId = unit.fieldId.includes(":")
      ? unit.fieldId.split(":")[0]!
      : unit.fieldId;
    missing.push({
      questionId: scrollId,
      label: unit.label ?? unit.fieldId,
      sectionId: sectionIdForFieldId(unit.fieldId),
    });
  }

  const missingBySection: Record<string, number> = {};
  for (const field of missing) {
    missingBySection[field.sectionId] = (missingBySection[field.sectionId] ?? 0) + 1;
  }

  return { ready: missing.length === 0, missing, missingBySection };
}

export { buildRequiredContext };

export function createRequiredContext(
  requiredFields: { id: string; label: string }[],
  questions: DsaQuestion[],
): RequiredContext {
  const context = buildRequiredContext(requiredFields, questions);
  for (const question of questions) {
    if (!context.fieldLabels.has(question.id)) {
      context.fieldLabels.set(question.id, question.text);
    }
    if (question.source_general_id && !context.fieldLabels.has(question.source_general_id)) {
      context.fieldLabels.set(question.source_general_id, question.text);
    }
  }
  return context;
}
