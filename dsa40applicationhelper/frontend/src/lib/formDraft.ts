import type { FormValues } from "$lib/conditions";

const STORAGE_PREFIX = "dsa40-form-draft:";
export const MIGRATE_FROM_KEY = "dsa40-migrate-from";
export const VIEW_MODE_KEY = "dsa40-form-view-mode";

export type FormViewMode = "sections" | "wizard";

export function draftStorageKey(vlopseIds: string[]): string {
  return STORAGE_PREFIX + [...vlopseIds].sort().join(",");
}

export function loadFormDraft(vlopseIds: string[]): FormValues | null {
  if (typeof localStorage === "undefined" || vlopseIds.length === 0) return null;
  try {
    const raw = localStorage.getItem(draftStorageKey(vlopseIds));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    return parsed as FormValues;
  } catch {
    return null;
  }
}

export function saveFormDraft(vlopseIds: string[], values: FormValues): void {
  if (typeof localStorage === "undefined" || vlopseIds.length === 0) return;
  try {
    localStorage.setItem(draftStorageKey(vlopseIds), JSON.stringify(values));
  } catch {
    // Ignore quota / private-mode errors.
  }
}

export function clearFormDraft(vlopseIds: string[]): void {
  if (typeof localStorage === "undefined") return;
  localStorage.removeItem(draftStorageKey(vlopseIds));
}

export function loadViewMode(): FormViewMode {
  if (typeof localStorage === "undefined") return "wizard";
  const stored = localStorage.getItem(VIEW_MODE_KEY);
  if (stored === "sections" || stored === "wizard") return stored;
  return "wizard";
}

export function saveViewMode(mode: FormViewMode): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(VIEW_MODE_KEY, mode);
}

export function mergeDraftValues(base: FormValues, previous: FormValues): FormValues {
  const merged = { ...base };
  for (const [key, value] of Object.entries(previous)) {
    if (!value?.trim()) continue;
    const current = merged[key]?.trim() ?? "";
    if (!current || current === "[]" || current === "{}") {
      merged[key] = value;
    }
  }
  return merged;
}

export function markDraftForMigration(vlopseIds: string[]): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.setItem(MIGRATE_FROM_KEY, draftStorageKey(vlopseIds));
}

export function consumeMigrationSource(): string | null {
  if (typeof sessionStorage === "undefined") return null;
  const key = sessionStorage.getItem(MIGRATE_FROM_KEY);
  sessionStorage.removeItem(MIGRATE_FROM_KEY);
  return key;
}

export function loadDraftByStorageKey(storageKey: string): FormValues | null {
  if (typeof localStorage === "undefined") return null;
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    return parsed as FormValues;
  } catch {
    return null;
  }
}
