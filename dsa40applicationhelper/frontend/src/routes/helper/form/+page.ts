import type { PageLoad } from "./$types";
export const prerender = false;
export const ssr = false;
import {
  apiQuestionsApplicableQuestions,
  apiConditionGetConditions,
  apiVlopseGetVlopse,
  type PlatformInformation,
} from "@api";
import type { PlatformLegalInfo } from "$lib/platformLegal";
import type { PlatformFieldIndex } from "$lib/transformErrors";

const loadConditions = async (vlopses: string[]) => {
  const call = await apiConditionGetConditions({
    query: { vlopse: vlopses },
  });
  const res = call.response;

  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return call.data;
};

export const load: PageLoad = async ({ url }) => {
  const vlopses = url.searchParams.getAll("vlopses");

  const [questionsCall, allPlatformsCall] = await Promise.all([
    apiQuestionsApplicableQuestions({ query: { vlopse: vlopses } }),
    apiVlopseGetVlopse(),
  ]);

  const res = questionsCall.response;
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  let questions = questionsCall.data?.map((e) => e && { validation: null, ...e }) ?? [];
  let conditions = await loadConditions(vlopses);

  let mappingIndex: PlatformFieldIndex = {};
  let requiredFields: { id: string; label: string }[] = [];
  if (vlopses.length > 0) {
    const params = new URLSearchParams();
    for (const id of vlopses) params.append("vlopse", id);
    const query = params.toString();
    const [mappingRes, requiredRes] = await Promise.all([
      fetch(`/api/platform-field-index?${query}`),
      fetch(`/api/required-fields?${query}`),
    ]);
    if (mappingRes.ok) {
      mappingIndex = (await mappingRes.json()) as PlatformFieldIndex;
    }
    if (requiredRes.ok) {
      requiredFields = (await requiredRes.json()) as { id: string; label: string }[];
    }
  }

  const platformById = new Map(
    (allPlatformsCall.data ?? []).map((entry) => [entry.id, entry.info]),
  );
  const platforms = vlopses
    .map((id) => {
      const info = platformById.get(id) as
        | (PlatformInformation & {
            disclaimers?: PlatformLegalInfo["disclaimers"];
            term_implications?: string[];
          })
        | undefined;
      if (!info) return null;
      return {
        id,
        name: info.name,
        applicationLink: info.application_link,
        modality: info.modality,
        disclaimers: info.disclaimers ?? [],
        termImplications: info.term_implications ?? [],
      };
    })
    .filter((p): p is NonNullable<typeof p> => p !== null);

  return { questions, conditions, platforms, vlopseIds: vlopses, mappingIndex, requiredFields };
};
