from collections import defaultdict

from typing_extensions import override

from app.core.config import get_vlopse_configuration_for
from app.core.models import PlatformMapping, UnifiedQuestion
from app.services.questions import QuestionService


class Mapping:
    vlopse_id: str
    dsa_ids: list[str]

    def __init__(self, vlopse_id: str, dsa_ids: list[str]) -> None:
        self.vlopse_id = vlopse_id
        self.dsa_ids = dsa_ids

    @override
    def __repr__(self):
        return f"DSA([{', '.join(self.dsa_ids)}]) -> VLOPSE({self.vlopse_id})"


def hydrate_mapping(vlopse_question: str, mapping_definition: PlatformMapping):
    from app.core.conditions_util import general_ids_from_mapping

    if isinstance(mapping_definition, str):
        return Mapping(vlopse_question, [mapping_definition])
    return Mapping(vlopse_question, general_ids_from_mapping(mapping_definition))


class MappingValidationError(Exception):
    pass


class QuestionMapper:
    _mapping: dict[str, list[Mapping]]
    questions: QuestionService

    @classmethod
    def from_vlopse_names(cls, vlopses: list[str], questions: QuestionService):
        mapping = {
            vlopse: get_vlopse_configuration_for(vlopse).mappings for vlopse in vlopses
        }
        return cls(mapping, questions)

    def _validate(self):
        question_ids = [q.id for q in self.questions.get_all_unified()]
        invalid_mappings: set[Mapping] = set()
        # TODO: Check if a mapping refers to a question not defined by the vlopse
        for vlopse, mappings in self._mapping.items():
            print(f"Validating {vlopse}..")
            for mapping in mappings:
                for u_id in mapping.dsa_ids:
                    if u_id not in question_ids:
                        invalid_mappings.add(mapping)
                        print(
                            f"[WARN] {mapping} for {vlopse} refers to {u_id}, which is undefined!"
                        )

        if len(invalid_mappings):
            msg = f"[ERROR] {len(invalid_mappings)} invalid mappings found.: {invalid_mappings}"
            raise MappingValidationError(msg)

    def __init__(
        self, mapping: dict[str, dict[str, PlatformMapping]], questions: QuestionService
    ) -> None:
        self._mapping = {
            vlopse: [
                hydrate_mapping(vlopse_question, operator)
                for vlopse_question, operator in mapping_definitions.items()
            ]
            for vlopse, mapping_definitions in mapping.items()
        }
        self.questions = questions

    def _map(self):
        result: dict[str, list[str]] = defaultdict(list)
        for _, mappings in self._mapping.items():
            for mapping in mappings:
                for dsa_id in mapping.dsa_ids:
                    result[dsa_id].append(mapping.vlopse_id)

        return result

    def map_vlopse_to_unified(self):
        map_traces = self._map()
        print(f"Mapped to {map_traces}")
        # FIXME: this should ask the db
        result: list[tuple[bool, UnifiedQuestion]] = []
        for dsa_id, vlopse_ids in map_traces.items():
            dsa = self.questions.get_unified(dsa_id)
            if dsa is None:
                print(f"WARNING {dsa_id} MAPPED TO UNKNOWN DSA QUESTION")
                continue
            required = False
            for vlopse_id in vlopse_ids:
                vlopse = self.questions.get(vlopse_id)
                if vlopse is None:
                    print(f"WARNING {vlopse_id} MAPPED TO UNKNOWN VLOPSE QUESTION")
                    continue
                # FIXME: Typing err
                if vlopse.required:
                    required = True
            result.append((required, dsa))

        return result
