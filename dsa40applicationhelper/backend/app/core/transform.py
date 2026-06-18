from app.core.mapping import Mapping, hydrate_mapping
from app.core.operator import (
    AbstractOperator,
    OperatorExecutionError,
    hydrate_operator,
)

from .config import get_vlopse_configuration_for
from .models import Answer, MappedAnswer, MappingError, MappingResult, PlatformMapping


class OperatorValidationError(Exception):
    def __init__(self, message: str, loc: tuple[str, ...]) -> None:
        super().__init__({"message": message, "loc": loc})


class ValidationErrors(ExceptionGroup):
    def derive(self, excs):
        return ValidationErrors(self.message, excs)


class TransformationError(Exception):
    def __init__(
        self, message: str, loc: tuple[str, ...], inputs: list[str], cause: str
    ) -> None:
        super().__init__(
            {"message": message, "loc": loc, "inputs": inputs, "cause": cause}
        )


class Transformation:
    mapping: Mapping
    operator: AbstractOperator

    def __init__(self, mapping: Mapping, operator: AbstractOperator) -> None:
        self.mapping = mapping
        self.operator = operator

    def validate_args(self, args: list[Answer]):
        if getattr(self.operator, "constant_output", False):
            return

        from app.core.platform_specific import ANSWER_KEY_SEP

        present: set[str] = set()
        for answer in args:
            qid = answer.question_id
            if ANSWER_KEY_SEP in qid:
                present.add(qid.rsplit(ANSWER_KEY_SEP, 1)[0])
            else:
                present.add(qid)
        missing = [
            dsa_question
            for dsa_question in self.mapping.dsa_ids
            if dsa_question not in present
        ]

        if not missing:
            return

        if (
            self.operator.needs_context
            and len(self.mapping.dsa_ids) > 1
            and len(present) > 0
        ):
            return

        if len(missing):
            es = [
                OperatorValidationError(message="missing required argument", loc=(m,))
                for m in missing
            ]
            raise ValidationErrors("missing arguments for {vlopse_question_id}", es)

    def transform(
        self,
        args: list[Answer],
        full_answer_map: dict[str, str | None] | None = None,
    ):
        try:
            local_map = {a.question_id: a.value for a in args}
            context_map = full_answer_map if full_answer_map is not None else local_map
            if len(args) == 0:
                result = self.operator.apply(None, context_map)
            elif len(args) == 1:
                result = self.operator.apply(args[0].value, context_map)
            else:
                result = self.operator.apply([a.value for a in args], context_map)
        except OperatorExecutionError as e:
            cause = e.args[0]
            loc = tuple([a.question_id for a in args])
            raise TransformationError(
                message="transformation failed",
                inputs=cause["inputs"],
                loc=loc,
                cause=cause["message"],
            ) from e
        return result


class AnswerTransformer:
    _mapping: dict[str, PlatformMapping]
    vlopse: str = ""
    _merged_conditions: dict[str, list] | None = None

    @classmethod
    def from_vlopse_name(cls, vlopse: str):
        mapping = get_vlopse_configuration_for(vlopse).mappings
        instance = cls(mapping)
        instance.vlopse = vlopse
        return instance

    def __init__(self, mapping: dict[str, PlatformMapping]) -> None:
        self._mapping = mapping

    def _merged_helper_conditions(self) -> dict[str, list]:
        if self._merged_conditions is None:
            from app.services.condition_service import ConditionService

            self._merged_conditions = ConditionService().get_merged_conditions(
                [self.vlopse]
            )
        return self._merged_conditions

    def _platform_question_required(self, platform_question_id: str) -> bool:
        from app.services.questions import QuestionService

        platform_q = QuestionService().get(platform_question_id)
        return bool(platform_q and platform_q.required)

    def _granularity_for(self, general_id: str) -> str | None:
        from app.services.question_store import load_unified_questions

        for record in load_unified_questions():
            if record.id == general_id:
                return record.granularity
        return None

    def _resolve_answer(
        self, general_id: str, answer_map: dict[str, Answer]
    ) -> Answer | None:
        from app.core.platform_specific import scoped_answer_id

        granularity = self._granularity_for(general_id)
        if granularity == "platform_specific" and self.vlopse:
            return answer_map.get(scoped_answer_id(general_id, self.vlopse))
        return answer_map.get(general_id)

    def _collect_inputs(
        self, operator: PlatformMapping, answer_map: dict[str, Answer], answers: list[Answer]
    ) -> list[Answer]:
        if isinstance(operator, str):
            resolved = self._resolve_answer(operator, answer_map)
            return [resolved] if resolved else []
        from app.core.models import PlatformMappingComplex
        from app.core.operator import operation_constant_output

        if isinstance(operator, PlatformMappingComplex) and operation_constant_output(
            operator.operation
        ):
            return []
        if operator.src is None:
            return []
        if isinstance(operator.src, list):
            inputs: list[Answer] = []
            for general_id in operator.src:
                resolved = self._resolve_answer(general_id, answer_map)
                if resolved:
                    inputs.append(resolved)
            return inputs
        if isinstance(operator.src, str):
            resolved = self._resolve_answer(operator.src, answer_map)
            return [resolved] if resolved else []
        raise TypeError(f"Unknown operation {operator}")

    def _get_mapping_operator(self, id: str):
        operator = self._mapping.get(id)
        return operator

    def transform(
        self, answers: list[Answer], mapper: Mapping, op: AbstractOperator
    ) -> MappingResult:
        transformation = Transformation(mapper, op)

        transformation.validate_args(answers)
        output = transformation.transform(answers)
        answer = MappedAnswer(question_id=mapper.vlopse_id, value=output)

        return answer

    def transform_safe(
        self,
        answers: list[Answer],
        mapper: Mapping,
        op: AbstractOperator,
        full_answer_map: dict[str, str | None] | None = None,
    ):
        transformation = Transformation(mapper, op)
        question_id = mapper.vlopse_id
        try:
            transformation.validate_args(answers)
            output = transformation.transform(answers, full_answer_map)
            answer = MappedAnswer(question_id=question_id, value=output)
        except ValidationErrors as e:
            errors = [
                {
                    "type": "type_error",
                    "loc": (question_id, *err.args[0]["loc"]),
                    "message": err.args[0]["message"],
                }
                for err in e.exceptions
            ]
            answer = MappingError(question_id=question_id, errors=errors)
        except TransformationError as e:
            e = e.args[0]
            loc = (*e["loc"], question_id)
            errors = [
                {
                    "type": "type_error",  # TODO: this could be more specific?
                    "loc": loc,
                    "message": e["message"],
                    "input": e["inputs"],
                }
            ]
            answer = MappingError(question_id=question_id, errors=errors)
            return answer

        return answer

    def _should_skip_empty_mapping(
        self,
        vlopse_question_id: str,
        mapper: Mapping,
        inputs: list[Answer],
        value_map: dict[str, str | None],
    ) -> bool:
        if inputs:
            return False
        from app.core.conditions_util import mapping_applicable_for_helper

        return not mapping_applicable_for_helper(
            vlopse=self.vlopse,
            general_ids=list(mapper.dsa_ids),
            platform_required=self._platform_question_required(vlopse_question_id),
            answer_map=value_map,
            merged_conditions=self._merged_helper_conditions(),
        )

    def map(self, answers: list[Answer]):
        answer_objects = {a.question_id: a for a in answers}
        value_map = {a.question_id: a.value for a in answers}
        result: list[MappingResult] = []
        for vlopse_question, operator in self._mapping.items():
            mapper = hydrate_mapping(vlopse_question, operator)
            op = hydrate_operator(operator)
            inputs = self._collect_inputs(operator, answer_objects, answers)
            if self._should_skip_empty_mapping(vlopse_question, mapper, inputs, value_map):
                result.append(MappedAnswer(question_id=mapper.vlopse_id, value=""))
                continue
            output = self.transform_safe(
                inputs,
                mapper,
                op,
                value_map if op.needs_context else None,
            )
            result.append(output)

        return result
