import type { DsaQuestion } from "@api/types.gen";
import { isVisible, type ConditionsMap, type FormValues } from "$lib/conditions";
import {
  COMPOSITE_FIELD_MAP,
  COMPOSITE_GATE_FIELDS,
  expandFormValues,
  SCHEMA_FIELDS,
} from "$lib/structured";

const ANSWER_KEY_SEP = "__";

/** Composite fields stored as per-platform dictionaries in JSON payloads. */
const PLATFORM_DICT_FIELD_IDS = new Set([
  "profile-platform",
  "prev-experience",
  "prev-experience-detail",
  "data-requested",
]);

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

function emptyValueForQuestion(question: DsaQuestion): string {
  if (question.input_type === "repeatable_group") return "[]";
  if (question.input_type === "composite_group") return "{}";
  return "";
}

function clearFlatFieldKeys(out: FormValues, fieldId: string): void {
  delete out[fieldId];
  for (const key of Object.keys(out)) {
    if (key.startsWith(`${fieldId}${ANSWER_KEY_SEP}`)) {
      delete out[key];
    }
  }
}

function platformDictValue(
  payload: Record<string, unknown>,
  fieldId: string,
  platformId: string,
): string {
  const raw = payload[fieldId];
  if (isPlatformScopedDict(raw)) {
    return String(raw[platformId] ?? "").trim();
  }
  if (typeof raw === "string") return raw.trim();
  return "";
}

function shouldShowPlatformPanel(
  fieldId: string,
  platformId: string,
  conditions: ConditionsMap,
  formValues: FormValues,
  payload: Record<string, unknown>,
): boolean {
  if (fieldId === "prev-experience-detail") {
    return platformDictValue(payload, "prev-experience", platformId) === "Yes";
  }
  const scopedKey = `${fieldId}${ANSWER_KEY_SEP}${platformId}`;
  if (conditions[scopedKey]?.length) {
    return isVisible(scopedKey, conditions, formValues);
  }
  return true;
}

function isCompositeFieldVisible(
  fieldId: string,
  schemaName: string,
  conditions: ConditionsMap,
  formValues: FormValues,
  vlopseIds: string[],
  payload: Record<string, unknown>,
): boolean {
  if ((COMPOSITE_GATE_FIELDS[schemaName] ?? []).includes(fieldId)) {
    return true;
  }
  if (PLATFORM_DICT_FIELD_IDS.has(fieldId)) {
    return vlopseIds.some((platformId) =>
      shouldShowPlatformPanel(fieldId, platformId, conditions, formValues, payload),
    );
  }
  return isVisible(fieldId, conditions, formValues);
}

function prunePlatformDictField(
  payload: Record<string, unknown>,
  fieldId: string,
  conditions: ConditionsMap,
  formValues: FormValues,
  vlopseIds: string[],
): void {
  const raw = payload[fieldId];
  if (!isPlatformScopedDict(raw)) {
    return;
  }

  const next: Record<string, string> = {};
  for (const platformId of vlopseIds) {
    if (!shouldShowPlatformPanel(fieldId, platformId, conditions, formValues, payload)) {
      continue;
    }
    const value = String(raw[platformId] ?? "").trim();
    if (value) next[platformId] = value;
  }

  if (Object.keys(next).length === 0) {
    delete payload[fieldId];
  } else {
    payload[fieldId] = next;
  }
}

function pruneCompositePayload(
  raw: string | undefined,
  compositeId: string,
  schemaName: string,
  conditions: ConditionsMap,
  formValues: FormValues,
  vlopseIds: string[],
): string {
  const payload = parseObject(raw);
  const fieldIds =
    COMPOSITE_FIELD_MAP[compositeId] ?? SCHEMA_FIELDS[schemaName] ?? [];

  for (const fieldId of fieldIds) {
    if (!isCompositeFieldVisible(fieldId, schemaName, conditions, formValues, vlopseIds, payload)) {
      delete payload[fieldId];
      continue;
    }
    if (PLATFORM_DICT_FIELD_IDS.has(fieldId)) {
      prunePlatformDictField(payload, fieldId, conditions, formValues, vlopseIds);
    }
  }

  return JSON.stringify(payload);
}

function isQuestionHidden(
  question: DsaQuestion,
  conditions: ConditionsMap,
  formValues: FormValues,
): boolean {
  if (question.required) return false;
  return !isVisible(question.id, conditions, formValues);
}

/**
 * Drop answers for fields that are not visible under current conditions.
 * Idempotent — safe to run multiple times. Intended after successful generation
 * so drafts stay intact while editing, but hidden stale data is removed once submitted.
 */
export function pruneHiddenFieldValues(
  values: FormValues,
  questions: DsaQuestion[],
  conditions: ConditionsMap,
  vlopseIds: string[],
): FormValues {
  const out: FormValues = { ...values };
  let formValues = expandFormValues(out);

  for (const question of questions) {
    if (!isQuestionHidden(question, conditions, formValues)) {
      continue;
    }

    out[question.id] = emptyValueForQuestion(question);
  }

  formValues = expandFormValues(out);

  for (const question of questions) {
    if (question.input_type === "composite_group") {
      const schemaName = String(question.config?.schema ?? "");
      const next = pruneCompositePayload(
        out[question.id],
        question.id,
        schemaName,
        conditions,
        formValues,
        vlopseIds,
      );
      if (next !== (out[question.id] ?? "{}")) {
        out[question.id] = next;
      }
    }
  }

  formValues = expandFormValues(out);

  const conditionPayload = buildConditionPayload(out);

  for (const fields of Object.values(COMPOSITE_FIELD_MAP)) {
    for (const fieldId of fields) {
      if (!isVisible(fieldId, conditions, formValues)) {
        clearFlatFieldKeys(out, fieldId);
      } else if (PLATFORM_DICT_FIELD_IDS.has(fieldId)) {
        for (const key of Object.keys(out)) {
          if (!key.startsWith(`${fieldId}${ANSWER_KEY_SEP}`)) continue;
          const platformId = key.slice(fieldId.length + ANSWER_KEY_SEP.length);
          if (!vlopseIds.includes(platformId)) {
            delete out[key];
            continue;
          }
          if (
            !shouldShowPlatformPanel(
              fieldId,
              platformId,
              conditions,
              formValues,
              conditionPayload,
            )
          ) {
            delete out[key];
          }
        }
      }
    }
  }

  return out;
}

function buildConditionPayload(values: FormValues): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const [compositeId, fields] of Object.entries(COMPOSITE_FIELD_MAP)) {
    Object.assign(payload, parseObject(values[compositeId]));
    for (const fieldId of fields) {
      for (const [key, rawValue] of Object.entries(values)) {
        if (!key.startsWith(`${fieldId}${ANSWER_KEY_SEP}`)) continue;
        const platformId = key.slice(fieldId.length + ANSWER_KEY_SEP.length);
        if (!rawValue?.trim()) continue;
        const existing = payload[fieldId];
        const dict = isPlatformScopedDict(existing)
          ? { ...(existing as Record<string, unknown>) }
          : {};
        dict[platformId] = rawValue.trim();
        payload[fieldId] = dict;
      }
    }
  }
  return payload;
}
