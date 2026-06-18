import type { DsaQuestion } from "@api/types.gen";
import type { ConditionsMap, FormValues } from "$lib/conditions";
import { isVisible } from "$lib/conditions";
import { isAnswerFilled } from "$lib/answerFilled";
import type { FormRow } from "$lib/formSections";
import {
  COMPOSITE_FIELD_MAP,
  COMPOSITE_GATE_FIELDS,
  parseItems,
  SCHEMA_FIELDS,
  expandFormValues,
} from "$lib/structured";

export type FieldUnit = {
  fieldId: string;
  label?: string;
  required: boolean;
  filled: boolean;
};

export type RequiredContext = {
  requiredFieldIds: Set<string>;
  requiredQuestionIds: Set<string>;
  fieldLabels: Map<string, string>;
};

function leafFilled(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return true;
  if (Array.isArray(value)) {
    return value.some((entry) => leafFilled(entry));
  }
  if (typeof value === "object") {
    return Object.values(value as Record<string, unknown>).some((entry) => leafFilled(entry));
  }
  return false;
}

function isLeafRequired(fieldId: string, required: RequiredContext): boolean {
  const baseId = fieldId.includes("__") ? fieldId.split("__")[0]! : fieldId;
  return required.requiredFieldIds.has(baseId);
}

function isQuestionRequired(question: DsaQuestion, required: RequiredContext): boolean {
  return (
    required.requiredQuestionIds.has(question.id) ||
    required.requiredFieldIds.has(question.id)
  );
}

function compositeFieldIds(question: DsaQuestion): string[] {
  const fromMap = COMPOSITE_FIELD_MAP[question.id];
  if (fromMap) return fromMap;
  const schemaName = String(question.config?.schema ?? "");
  return SCHEMA_FIELDS[schemaName] ?? [];
}

function parseCompositePayload(raw: string | undefined): Record<string, unknown> {
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

function compositeSchemaName(question: DsaQuestion): string {
  return String(question.config?.schema ?? "");
}

function isGateField(schemaName: string, fieldId: string): boolean {
  return (COMPOSITE_GATE_FIELDS[schemaName] ?? []).includes(fieldId);
}

function expandCompositeUnits(
  question: DsaQuestion,
  values: FormValues,
  expandedValues: Record<string, string | undefined>,
  conditions: ConditionsMap,
  required: RequiredContext,
): FieldUnit[] {
  const fieldIds = compositeFieldIds(question);
  if (!fieldIds.length) {
    return [
      {
        fieldId: question.id,
        label: question.text,
        required: isQuestionRequired(question, required),
        filled: isAnswerFilled(values[question.id], question.input_type),
      },
    ];
  }

  const payload = parseCompositePayload(values[question.id]);
  const units: FieldUnit[] = [];
  const schemaName = compositeSchemaName(question);

  for (const fieldId of fieldIds) {
    if (!isGateField(schemaName, fieldId) && !isVisible(fieldId, conditions, expandedValues)) {
      continue;
    }
    units.push({
      fieldId,
      label: required.fieldLabels.get(fieldId) ?? fieldId,
      required: isLeafRequired(fieldId, required),
      filled: leafFilled(payload[fieldId]),
    });
  }

  return units;
}

function expandRepeatableUnits(
  question: DsaQuestion,
  values: FormValues,
  expandedValues: Record<string, string | undefined>,
  conditions: ConditionsMap,
  required: RequiredContext,
): FieldUnit[] {
  const schemaName = String(question.config?.schema ?? "");
  const items = parseItems(values[question.id] ?? "[]");
  const minItems = Number(question.config?.min_items ?? 0);
  const questionRequired = isQuestionRequired(question, required);

  if (items.length === 0 && minItems > 0 && questionRequired) {
    return [
      {
        fieldId: question.id,
        label: question.text,
        required: true,
        filled: false,
      },
    ];
  }

  const effectiveCount = Math.max(
    items.length,
    minItems > 0 ? minItems : items.length > 0 ? items.length : 0,
  );

  if (effectiveCount === 0) return [];

  if (schemaName === "team-member") {
    const units: FieldUnit[] = [];
    const personFields = SCHEMA_FIELDS["person-profile"] ?? [];
    const affiliationFields = SCHEMA_FIELDS["affiliation-profile"] ?? [];

    for (let index = 0; index < effectiveCount; index += 1) {
      const item = items[index] ?? {};
      const person = (item.person as Record<string, unknown> | undefined) ?? {};
      for (const fieldId of personFields) {
        if (!isVisible(fieldId, conditions, expandedValues)) continue;
        units.push({
          fieldId: `${question.id}:${index}:person:${fieldId}`,
          label: required.fieldLabels.get(fieldId) ?? fieldId,
          required: isLeafRequired(fieldId, required),
          filled: leafFilled(person[fieldId]),
        });
      }

      const affiliations = (item.affiliations as Record<string, unknown>[] | undefined) ?? [];
      const affiliationCount = Math.max(affiliations.length, 1);
      for (let affIndex = 0; affIndex < affiliationCount; affIndex += 1) {
        const affiliation = affiliations[affIndex] ?? {};
        for (const fieldId of affiliationFields) {
          if (fieldId === "organisation_id") continue;
          if (!isVisible(fieldId, conditions, expandedValues)) continue;
          units.push({
            fieldId: `${question.id}:${index}:aff:${affIndex}:${fieldId}`,
            label: required.fieldLabels.get(fieldId) ?? fieldId,
            required: isLeafRequired(fieldId, required),
            filled: leafFilled(affiliation[fieldId]),
          });
        }
      }
    }
    return units;
  }

  const fieldIds = SCHEMA_FIELDS[schemaName] ?? [];
  if (!fieldIds.length) {
    return [
      {
        fieldId: question.id,
        label: question.text,
        required: questionRequired,
        filled: isAnswerFilled(values[question.id], question.input_type),
      },
    ];
  }

  const units: FieldUnit[] = [];
  for (let index = 0; index < effectiveCount; index += 1) {
    const item = items[index] ?? {};
    for (const fieldId of fieldIds) {
      if (!isVisible(fieldId, conditions, expandedValues)) continue;
      units.push({
        fieldId: `${question.id}:${index}:${fieldId}`,
        label: required.fieldLabels.get(fieldId) ?? fieldId,
        required: isLeafRequired(fieldId, required),
        filled: leafFilled(item[fieldId]),
      });
    }
  }
  return units;
}

function expandRowToFieldUnits(
  row: FormRow,
  visibility: Record<string, boolean>,
  values: FormValues,
  conditions: ConditionsMap,
  required: RequiredContext,
): FieldUnit[] {
  const expandedValues = expandFormValues(values);

  if (row.kind === "platform_group") {
    return row.variants
      .filter((variant) => visibility[variant.id] || variant.required)
      .map((variant) => ({
        fieldId: variant.id,
        label: variant.text,
        required:
          variant.required ||
          (variant.source_general_id
            ? isLeafRequired(variant.source_general_id, required)
            : false),
        filled: isAnswerFilled(values[variant.id], variant.input_type),
      }));
  }

  const question = row.question;
  const questionVisible = visibility[question.id] ?? true;
  if (!questionVisible && !question.required) return [];

  if (question.input_type === "composite_group") {
    return expandCompositeUnits(question, values, expandedValues, conditions, required);
  }

  if (question.input_type === "repeatable_group") {
    return expandRepeatableUnits(question, values, expandedValues, conditions, required);
  }

  return [
    {
      fieldId: question.id,
      label: question.text,
      required: isQuestionRequired(question, required),
      filled: isAnswerFilled(values[question.id], question.input_type),
    },
  ];
}

export function fieldUnitsForRows(
  rows: FormRow[],
  visibility: Record<string, boolean>,
  values: FormValues,
  conditions: ConditionsMap,
  required: RequiredContext,
): FieldUnit[] {
  const units: FieldUnit[] = [];
  for (const row of rows) {
    units.push(...expandRowToFieldUnits(row, visibility, values, conditions, required));
  }
  return units;
}

export function buildRequiredContext(
  requiredFields: { id: string; label: string }[],
  questions: DsaQuestion[],
): RequiredContext {
  return {
    requiredFieldIds: new Set(requiredFields.map((field) => field.id)),
    requiredQuestionIds: new Set(questions.filter((q) => q.required).map((q) => q.id)),
    fieldLabels: new Map(requiredFields.map((field) => [field.id, field.label])),
  };
}
