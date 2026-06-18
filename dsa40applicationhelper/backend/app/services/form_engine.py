from pycountry import countries

from app.core.answer_projection import (
    COMPOSITE_FIELD_MAP,
    composites_for_mapped_fields,
    expand_answers,
    is_embedded_field,
)
from app.core.schema_registry import composite_owner_for_field
from app.core.mapping import QuestionMapper
from app.core.structured_schemas import (
    validate_composite_answer,
    validate_repeatable_answer,
)
from app.schemas import Selection, config_adapter
from app.core.models import (
    Answer,
    ErrorDetails,
    MappingError,
    MappingResult,
)
from app.core.transform import AnswerTransformer
from app.models import DSAQuestion, InputType, VLOPSEQuestion
from app.services.questions import QuestionService


class AnswerToUnknownQuestion(BaseException):
    pass


from app.core.conditions_util import (
    COLLAB_BASIC_FIELD_IDS,
    COLLAB_SHARE_SUPPLEMENT_IDS,
    COLLAB_SHARE_TRIGGER_IDS,
    COLLAB_TRIGGER_IDS,
    collab_structured_required,
    collab_supplements_for,
    FUNDING_TRIGGER_IDS,
    FUNDING_SUPPLEMENT_GENERAL_IDS,
    ORG_AFFILIATION_SUPPLEMENT_COMPOSITE_IDS,
    ORG_AFFILIATION_TRIGGER_IDS,
    PURPOSE_LIMITATION_SUPPLEMENT_IDS,
    PURPOSE_LIMITATION_TRIGGER_IDS,
    PUBLICATION_TRIGGER_IDS,
    PUBLICATION_SUPPLEMENT_GENERAL_IDS,
)

PUBLICATION_SUPPLEMENT_IDS = tuple(PUBLICATION_SUPPLEMENT_GENERAL_IDS)
FUNDING_SUPPLEMENT_IDS = tuple(FUNDING_SUPPLEMENT_GENERAL_IDS)


class FormService:
    def __init__(self) -> None:
        self.question_service = QuestionService()
        pass

    def compute_options(self, question: DSAQuestion, vlopses: list[str]) -> list[str] | None:
        from app.core.platform_specific import ANSWER_KEY_SEP

        lookup_id = question.id
        if ANSWER_KEY_SEP in lookup_id:
            lookup_id = lookup_id.rsplit(ANSWER_KEY_SEP, 1)[0]

        if question.input_type == InputType.ISO_3166_1:
            return [c.name for c in countries]

        merged: list[str] = []
        seen: set[str] = set()

        def add_options(options: list[str]) -> None:
            for option in options:
                if option and option not in seen:
                    seen.add(option)
                    merged.append(option)

        if question.input_type in (InputType.composite_group, InputType.repeatable_group):
            return None

        if question.config:
            cfg = config_adapter.validate_python(question.config)
            if isinstance(cfg, Selection):
                add_options(cfg.options)

        mapper = QuestionMapper.from_vlopse_names(vlopses, self.question_service)
        for dsa_id, vlopse_ids in mapper._map().items():
            if dsa_id != lookup_id:
                continue
            for vlopse_id in vlopse_ids:
                vlopse_q = self.question_service.get(vlopse_id)
                if not vlopse_q or not vlopse_q.config:
                    continue
                cfg = config_adapter.validate_python(vlopse_q.config)
                if isinstance(cfg, Selection):
                    add_options(cfg.options)

        return merged if merged else None

    def validate_vlopse_question(self, question: VLOPSEQuestion, answer: Answer): ...
    def map_unified_to_vlopse_and_validate(
        self, answers: list[Answer], vlopses: list[str]
    ):
        ok = True
        errors: dict[str, list[ErrorDetails]] = {}
        for klops in vlopses:
            transformer = AnswerTransformer.from_vlopse_name(klops)
            transformed = transformer.map(expand_answers(answers, vlopses=vlopses))
            if any(isinstance(t, MappingError) for t in transformed):
                ok = False
                for t in transformed:
                    if isinstance(t, MappingError):
                        errors[t.question_id] = t.errors

        return ok, errors

    def validate_unified_question(self, answers: list[Answer], vlopses: list[str]):
        result: dict[str, str] = {}
        mapped = self.get_mapped_questions_for(vlopses)
        answer_by_id = {a.question_id: a.value for a in answers}

        for a in answers:
            qs = [(req, q) for req, q in mapped if q.id == a.question_id]

            if not len(qs):
                raise AnswerToUnknownQuestion(f"{a.question_id} not defined!")
            is_required, q = qs[0]

            if is_required and (a.value is None or a.value == ""):
                result[q.id] = "None or empty string not allowed"
                continue

            if q.input_type in (InputType.repeatable_group, InputType.composite_group):
                config = q.config or {}
                schema_name = str(config.get("schema") or "")
                if q.input_type == InputType.composite_group:
                    if a.value is not None:
                        error = validate_composite_answer(
                            a.value,
                            schema_name=schema_name,
                        )
                        if error:
                            result[q.id] = error
                    continue
                min_items = int(config.get("min_items") or 0)
                max_items = config.get("max_items")
                team_orgs_raw = answer_by_id.get("team-organisations")
                if a.value is not None:
                    error = validate_repeatable_answer(
                        a.value,
                        schema_name=schema_name,
                        min_items=min_items,
                        max_items=int(max_items) if max_items is not None else None,
                        team_orgs_raw=team_orgs_raw,
                    )
                    if error:
                        result[q.id] = error
                continue

            config = q.parsed_config

            if config and a.value is not None:
                error = config.validate_answer(a.value)
                if error:
                    result[q.id] = error
        return result

    def get_mapped_questions_for(self, vlopses: list[str]):
        from app.core.config import get_vlopse_configuration_for
        from app.core.platform_specific import scoped_answer_id, vlopse_maps_to_general
        from app.services.question_store import UnifiedQuestionRecord

        mapper = QuestionMapper.from_vlopse_names(vlopses, self.question_service)
        map_traces = mapper._map()
        mapped_general = set(map_traces.keys())
        structured_collab = collab_structured_required(mapped_general)
        result: list[tuple[bool, UnifiedQuestionRecord]] = []
        composite_ids = set(composites_for_mapped_fields(mapped_general))

        for general_id, platform_field_ids in map_traces.items():
            if structured_collab and general_id in COLLAB_BASIC_FIELD_IDS:
                continue
            owner = composite_owner_for_field(general_id)
            if (
                owner
                and owner in composite_ids
                and is_embedded_field(general_id)
            ):
                continue
            dsa = self.question_service.get_unified(general_id)
            if dsa is None:
                continue
            required = False
            for platform_field_id in platform_field_ids:
                platform_q = self.question_service.get(platform_field_id)
                if platform_q and platform_q.required:
                    required = True

            if dsa.granularity == "platform_specific":
                from app.core.platform_specific import (
                    META_DATA_REQUESTED_HELP,
                    format_platform_placeholder,
                )

                for vlopse in vlopses:
                    if not vlopse_maps_to_general(vlopse, general_id):
                        continue
                    info = get_vlopse_configuration_for(vlopse).info
                    label = format_platform_placeholder(dsa.text, [info.name])
                    help_text = dsa.help_text
                    if general_id == "data-requested":
                        help_text = (
                            META_DATA_REQUESTED_HELP if vlopse == "meta" else None
                        )
                    scoped = UnifiedQuestionRecord(
                        id=scoped_answer_id(general_id, vlopse),
                        text=label,
                        input_type=dsa.input_type,
                        help_text=help_text,
                        config=dsa.config,
                        category=dsa.category,
                        granularity=dsa.granularity,
                    )
                    result.append((required, scoped))
            else:
                result.append((required, dsa))

        present_ids = {record.id for _, record in result}
        for composite_id in composites_for_mapped_fields(set(map_traces.keys())):
            if composite_id in present_ids:
                continue
            composite = self.question_service.get_unified(composite_id)
            if composite is None:
                continue
            required = False
            for field_id in COMPOSITE_FIELD_MAP.get(composite_id, ()):
                for platform_field_id in map_traces.get(field_id, ()):
                    platform_q = self.question_service.get(platform_field_id)
                    if platform_q and platform_q.required:
                        required = True
            result.append((required, composite))

        if any(gid in COLLAB_TRIGGER_IDS for gid in map_traces):
            present_ids = {record.id for _, record in result}
            for supplement_id in collab_supplements_for(mapped_general):
                if supplement_id in present_ids:
                    continue
                supplement = self.question_service.get_unified(supplement_id)
                if supplement:
                    result.append((False, supplement))

        if any(gid in PUBLICATION_TRIGGER_IDS for gid in map_traces):
            present_ids = {record.id for _, record in result}
            for supplement_id in PUBLICATION_SUPPLEMENT_IDS:
                if supplement_id in present_ids:
                    continue
                supplement = self.question_service.get_unified(supplement_id)
                if supplement:
                    result.append((False, supplement))

        if any(gid in FUNDING_TRIGGER_IDS for gid in map_traces):
            present_ids = {record.id for _, record in result}
            for supplement_id in FUNDING_SUPPLEMENT_IDS:
                if supplement_id in present_ids:
                    continue
                supplement = self.question_service.get_unified(supplement_id)
                if supplement:
                    result.append((False, supplement))

        if any(gid in ORG_AFFILIATION_TRIGGER_IDS for gid in map_traces):
            present_ids = {record.id for _, record in result}
            for composite_id in ORG_AFFILIATION_SUPPLEMENT_COMPOSITE_IDS:
                if composite_id in present_ids:
                    continue
                composite = self.question_service.get_unified(composite_id)
                if composite:
                    result.append((False, composite))

        if any(gid in PURPOSE_LIMITATION_TRIGGER_IDS for gid in map_traces):
            present_ids = {record.id for _, record in result}
            for supplement_id in PURPOSE_LIMITATION_SUPPLEMENT_IDS:
                if supplement_id in present_ids:
                    continue
                supplement = self.question_service.get_unified(supplement_id)
                if supplement:
                    result.append((False, supplement))

        if any(gid in COLLAB_SHARE_TRIGGER_IDS for gid in map_traces):
            present_ids = {record.id for _, record in result}
            for supplement_id in COLLAB_SHARE_SUPPLEMENT_IDS:
                if supplement_id in present_ids:
                    continue
                supplement = self.question_service.get_unified(supplement_id)
                if supplement:
                    result.append((False, supplement))

        return result

    def get_required_general_ids(self, vlopses: list[str]) -> set[str]:
        mapper = QuestionMapper.from_vlopse_names(vlopses, self.question_service)
        map_traces = mapper._map()
        required: set[str] = set()
        for general_id, platform_field_ids in map_traces.items():
            for platform_field_id in platform_field_ids:
                platform_q = self.question_service.get(platform_field_id)
                if platform_q and platform_q.required:
                    required.add(general_id)
                    break
        return required

    def enhance_with_text(self, val: MappingError | MappingResult):
        q = self.question_service.get(val.question_id)
        if q:
            text = str(q.text)
        else:
            text = "N/A"
        v = val.model_dump()
        v["text"] = text
        return v

    def transform_answers_to_vlopse_answers(
        self, vlopses: list[str], answers: list[Answer]
    ):
        result = []
        for klops in vlopses:
            transformer = AnswerTransformer.from_vlopse_name(klops)
            transformed = [
                self.enhance_with_text(t)
                for t in transformer.map(expand_answers(answers, vlopses=vlopses))
            ]
            result.append((klops, transformed))
        return result
