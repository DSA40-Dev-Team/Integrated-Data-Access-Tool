import type { InputType } from "@api/types.gen";

function hasNonEmptyContent(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return true;
  if (Array.isArray(value)) {
    return value.some((entry) => hasNonEmptyContent(entry));
  }
  if (typeof value === "object") {
    return Object.values(value as Record<string, unknown>).some((entry) =>
      hasNonEmptyContent(entry),
    );
  }
  return false;
}

function isStructurallyEmpty(raw: string): boolean {
  try {
    const parsed = JSON.parse(raw);
    return !hasNonEmptyContent(parsed);
  } catch {
    return false;
  }
}

export function isAnswerFilled(
  value: string | undefined,
  inputType?: InputType,
): boolean {
  if (value === undefined) return false;
  const trimmed = value.trim();
  if (!trimmed) return false;
  if (trimmed === "[]" || trimmed === "{}") return false;

  if (inputType === "composite_group" || inputType === "repeatable_group") {
    return !isStructurallyEmpty(trimmed);
  }

  return true;
}
