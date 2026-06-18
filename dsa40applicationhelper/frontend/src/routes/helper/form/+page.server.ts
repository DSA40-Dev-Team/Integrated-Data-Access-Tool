import { fail } from "@sveltejs/kit";
import type { Actions } from "./$types";
import { apiTransformTransformAnswers, apiValidateValidateAnswers } from "@api";
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";
import { env } from "$env/dynamic/private";

const getBaseUrl = () => env.BACKEND_URL ?? "http://localhost:8000";

const validate = async ({ answers, vlopses }) => {
  const call = await apiValidateValidateAnswers({
    baseUrl: getBaseUrl(),
    body: { answers: answers },
    query: { vlopse: vlopses },
  });
  const res = call.response;

  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  let { ok, errors, kind } = call.data;
  if (ok) {
    return { ok: true, errors: [] };
  }

  let err =
    kind == "validation"
      ? {
          validation_errors: Object.entries(errors).map(([key, value]) => ({
            question_id: key,
            description: value,
          })),
        }
      : { transformation_errors: errors };

  return { ok: false, ...err };
};

const transform = async ({ answers, vlopses }) => {
  const call = await apiTransformTransformAnswers({
    baseUrl: getBaseUrl(),
    body: { answers: answers },
    query: { vlopse: vlopses },
  });
  const res = call.response;

  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  let by_vlopse = call.data.by_vlopse;
  return { ok: true, by_vlopse };
};

async function answersFromFormData(data: FormData) {
  const uploadDir = "/tmp/dsa_uploads";
  await mkdir(uploadDir, { recursive: true });
  return Promise.all(
    [...data.entries()].map(async ([key, value]) => {
      if (value instanceof File) {
        if (value.size > 0) {
          const filename = `${Date.now()}_${value.name}`;
          await writeFile(
            join(uploadDir, filename),
            Buffer.from(await value.arrayBuffer()),
          );
          return { question_id: key, value: join(uploadDir, filename) };
        }
        return { question_id: key, value: "" };
      }
      return { question_id: key, value: value as string };
    }),
  );
}

async function submitAnswers({ url, request }) {
  const vlopses = url.searchParams.getAll("vlopses");
  const data = await request.formData();
  const answers = await answersFromFormData(data);

  const { ok, ...rest } = await validate({ answers, vlopses });
  if (!ok) {
    return fail(400, { ...rest });
  }

  const transformResult = await transform({ answers, vlopses });
  return { success: true, by_vlopse: transformResult.by_vlopse };
}

export const actions = {
  default: submitAnswers,
} satisfies Actions;
