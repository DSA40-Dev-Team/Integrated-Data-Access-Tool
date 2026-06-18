from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.models import Answer, ErrorDetails, MappedAnswer, MappingError
from app.models import InputType
from app.services.condition_service import ConditionService
from app.services.form_engine import FormService
from app.services.questions import QuestionService
from app.services.vlopse import VlopseConfigService

from .schemas.form import DSAQuestion

router = APIRouter()

service = VlopseConfigService()
form_service = FormService()
question_service = QuestionService()
condition_service = ConditionService()


class PostDSAQuestionRequest(BaseModel):
    id: str
    text: str
    input_type: InputType
    help_text: str | None = None
    config: dict[str, str] | None = None


@router.post("/api/question")
async def add_dsa_question(question: PostDSAQuestionRequest):
    question_service.add_unified(**question.model_dump())
    return {"success": True}


@router.get("/api/question/{id}")
async def get_dsa_question(id: str):
    return question_service.get_unified(id)


@router.get("/api/question")
async def get_all_dsa_questions():
    return question_service.get_all_unified()


@router.get("/api/questions")
async def applicable_questions(vlopse: list[str] = Query(...)) -> list[DSAQuestion]:
    selected_vlopses = vlopse or []
    vlopses = service.get_all()
    print(f"Asking for {vlopse}")
    missing = [s for s in selected_vlopses if s not in vlopses]
    if len(missing):
        raise HTTPException(status_code=322, detail=f"Unknown vlopse(s): {missing}")

    qs = form_service.get_mapped_questions_for(vlopse)

    response: list[DSAQuestion] = []
    for req, q in qs:
        res = DSAQuestion.model_validate(q)
        if q.granularity == "platform_specific" and "__" in q.id:
            general_id, scoped_vlopse = q.id.rsplit("__", 1)
            res.source_general_id = general_id
            res.vlopse = scoped_vlopse
            unified = question_service.get_unified(general_id)
            if unified is not None:
                from app.core.config import get_vlopse_configuration_for
                from app.core.platform_specific import (
                    format_platform_placeholder,
                    vlopses_mapping_general,
                )

                mapped = vlopses_mapping_general(vlopse, general_id)
                platform_names = [
                    get_vlopse_configuration_for(v).info.name for v in mapped
                ]
                res.group_text = format_platform_placeholder(unified.text, platform_names)
        res.granularity = q.granularity or "general"
        opts = form_service.compute_options(q, vlopse)
        if opts is not None and res.options is None:
            res.options = opts
        res.required = req
        response.append(res)

    print(f"Returning {len(response)} DSA questions..")

    return response


class MappedAnswerWithText(MappedAnswer):
    text: str


class MappingErrorWithText(MappingError):
    text: str


MappingResultWithText = Annotated[
    MappedAnswerWithText | MappingErrorWithText, Field(discriminator="type")
]


class AnswerRequest(BaseModel):
    answers: list[Answer]


class TransformResponseForVlopse(BaseModel):
    name: str
    answers: list[MappingResultWithText]


class TransformResponse(BaseModel):
    by_vlopse: list[TransformResponseForVlopse]


class ValidationResponse(BaseModel):
    errors: dict[str, list[ErrorDetails] | str]
    ok: bool
    kind: Literal["validation", "transformation"]


class PlatformFieldSource(BaseModel):
    vlopse: str
    platform_id: str
    platform_text: str
    general_ids: list[str]
    helper_labels: list[str]
    helper_section: str | None = None


_COMPOSITE_SECTION_LABELS: dict[str, str] = {
    "primary-person": "About you",
    "primary-organisation": "Organisation",
    "primary-affiliation": "Organisation",
    "research-project": "Research project",
    "data-request": "Data request",
    "security-tom": "Security & TOM",
    "collaboration": "Collaboration",
    "funding": "Funding",
    "funding-entries": "Funding",
    "team-organisations": "Collaboration",
    "collab-researchers": "Collaboration",
}


@router.get("/api/platform-field-index")
async def platform_field_index(
    vlopse: list[str] = Query(...),
) -> dict[str, PlatformFieldSource]:
    from app.core.conditions_util import general_ids_from_mapping
    from app.core.config import get_vlopse_configuration_for
    from app.core.schema_registry import composite_owner_for_field

    unified = {q.id: q.text for q in question_service.get_all_unified()}
    index: dict[str, PlatformFieldSource] = {}

    for vlopse_name in vlopse:
        config = get_vlopse_configuration_for(vlopse_name)
        for platform_id, entry in config.mappings.items():
            general_ids = general_ids_from_mapping(entry)
            if not general_ids:
                continue
            platform_q = question_service.get(platform_id)
            helper_labels = [unified.get(gid, gid) for gid in general_ids]
            owner = composite_owner_for_field(general_ids[0])
            helper_section = _COMPOSITE_SECTION_LABELS.get(owner or "", None)
            if helper_section is None and general_ids[0].startswith("tech-"):
                helper_section = "Google technical"
            if helper_section is None and general_ids[0].startswith("meta-"):
                helper_section = "Meta"

            index[platform_id] = PlatformFieldSource(
                vlopse=vlopse_name,
                platform_id=platform_id,
                platform_text=platform_q.text if platform_q else platform_id,
                general_ids=general_ids,
                helper_labels=helper_labels,
                helper_section=helper_section,
            )

    return index


class RequiredFieldInfo(BaseModel):
    id: str
    label: str


@router.get("/api/required-fields")
async def required_fields(vlopse: list[str] = Query(...)) -> list[RequiredFieldInfo]:
    unified = {q.id: q.text for q in question_service.get_all_unified()}
    required_ids = form_service.get_required_general_ids(vlopse)
    return [
        RequiredFieldInfo(id=field_id, label=unified.get(field_id, field_id))
        for field_id in sorted(required_ids)
    ]


@router.post("/api/validate")
async def validate_answers(
    answers: AnswerRequest, vlopse: list[str] = Query(...)
) -> ValidationResponse:
    answers_inner = answers.answers
    print("Checking answers..")
    result = form_service.validate_unified_question(answers_inner, vlopse)
    print(result)
    kind = "validation"
    ok = len(result) == 0
    print(f"Ok: {ok}")
    if ok:
        ok, result = form_service.map_unified_to_vlopse_and_validate(
            answers_inner, vlopse
        )
        kind = "transformation"
    return ValidationResponse(errors=result, ok=ok, kind=kind)


@router.post("/api/transform")
async def transform_answers(answers: AnswerRequest, vlopse: list[str] = Query(...)):
    answers_inner = answers.answers
    result = form_service.transform_answers_to_vlopse_answers(vlopse, answers_inner)
    res = [TransformResponseForVlopse(name=name, answers=res) for name, res in result]

    print(f"TRANSFORM RESULT {result}")

    response = TransformResponse(by_vlopse=res)

    return response


@router.get("/api/condition")
async def get_conditions(vlopse: list[str] = Query(...)):
    conditions = condition_service.get_merged_conditions(vlopse)
    return conditions


@router.get("/api/schemas/{name}")
async def get_schema(name: str, vlopse: list[str] = Query(default=[])):
    from app.core.structured_schemas import load_schema, schema_field_metadata

    try:
        schema = load_schema(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown schema: {name}")
    return {
        "name": name,
        "schema": schema,
        "fields": schema_field_metadata(name, vlopses=vlopse or None),
    }
