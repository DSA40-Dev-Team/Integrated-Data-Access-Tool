import { COMPOSITE_FIELD_MAP } from "$lib/structured";

export type PlatformFieldSource = {
  vlopse: string;
  platform_id: string;
  platform_text: string;
  general_ids: string[];
  helper_labels: string[];
  helper_section: string | null;
};

export type PlatformFieldIndex = Record<string, PlatformFieldSource>;

export type TransformErrorEntry = {
  message: string;
};

const COMPOSITE_BY_FIELD: Record<string, string> = {};
for (const [compositeId, fields] of Object.entries(COMPOSITE_FIELD_MAP)) {
  for (const fieldId of fields) {
    COMPOSITE_BY_FIELD[fieldId] = compositeId;
  }
}

function helperScrollTarget(
  generalId: string,
  questionById: Map<string, string>,
): string {
  const base = generalId.split("__")[0]!;
  if (questionById.has(base)) return base;
  return COMPOSITE_BY_FIELD[base] ?? base;
}

export function scrollToHelperField(questionId: string) {
  document
    .querySelector(`[data-question-id="${questionId}"]`)
    ?.scrollIntoView({ behavior: "smooth", block: "center" });
}

export function resolveTransformErrorTarget(
  platformFieldId: string,
  index: PlatformFieldIndex,
  questionById: Map<string, string>,
): {
  platformLabel: string;
  helperQuestionIds: string[];
  helperLabels: string[];
  sectionLabel: string | null;
} {
  const source = index[platformFieldId];
  if (!source) {
    return {
      platformLabel: platformFieldId,
      helperQuestionIds: [],
      helperLabels: [],
      sectionLabel: null,
    };
  }

  const helperQuestionIds = [
    ...new Set(
      source.general_ids.map((gid) => helperScrollTarget(gid, questionById)),
    ),
  ];

  const helperLabels =
    source.helper_labels.length > 0
      ? source.helper_labels
      : source.general_ids.map((id) => id.split("__")[0]!);

  return {
    platformLabel: `${source.platform_text} (${source.vlopse.toUpperCase()} ${platformFieldId})`,
    helperQuestionIds,
    helperLabels,
    sectionLabel: source.helper_section,
  };
}
