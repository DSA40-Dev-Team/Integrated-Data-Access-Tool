from collections import defaultdict

from app.core.conditions_util import (
    COLLAB_BASIC_FIELD_IDS,
    COLLAB_SHARE_SUPPLEMENT_IDS,
    COLLAB_STRUCTURED_SUPPLEMENT_IDS,
    GOOGLE_TECH_FIELD_IDS,
    PURPOSE_LIMITATION_SUPPLEMENT_IDS,
    collab_share_relevant,
    collab_structured_required,
    covered_general_targets,
    general_condition_triggers,
    google_tech_client_condition_groups,
    mapped_general_ids,
    platform_conditions_to_general_groups,
    purpose_limitation_relevant,
    scoped_condition_key,
)
from app.core.platform_specific import scoped_answer_id
from app.core.config import get_vlopse_configuration_for
from app.core.models import Condition
from app.services.condition_store import load_general_conditions
from app.services.questions import QuestionService


def _scope_condition_groups(
    or_groups: list[list[Condition]], vlopse: str
) -> list[list[Condition]]:
    """Scope trigger question ids for platform-specific fields."""
    scoped: list[list[Condition]] = []
    for group in or_groups:
        scoped.append(
            [
                Condition(
                    question_id=scoped_condition_key(clause.question_id, vlopse),
                    operator=clause.operator,
                    value=clause.value,
                )
                for clause in group
            ]
        )
    return scoped


class ConditionService:
    question_service: QuestionService

    def __init__(self) -> None:
        self.question_service = QuestionService()

    def get_conditions(self, for_vlopses: list[str]):
        return {
            vlopse: get_vlopse_configuration_for(vlopse).conditions
            for vlopse in for_vlopses
        }

    def get_merged_conditions(
        self, for_vlopses: list[str]
    ) -> dict[str, list[list[Condition]]]:
        """General question id → OR of AND-groups for the unified helper form."""
        merged: dict[str, list[list[Condition]]] = defaultdict(list)
        covered: set[str] = set()
        mapped_all: set[str] = set()

        for vlopse in for_vlopses:
            config = get_vlopse_configuration_for(vlopse)
            mapped_all |= mapped_general_ids(config.mappings)
            groups = platform_conditions_to_general_groups(
                config.mappings, config.conditions
            )
            covered |= covered_general_targets(config.mappings, config.conditions)
            for general_id, or_groups in groups.items():
                merged[scoped_condition_key(general_id, vlopse)].extend(
                    _scope_condition_groups(or_groups, vlopse)
                )
            if vlopse == "google":
                covered |= GOOGLE_TECH_FIELD_IDS
                for general_id, or_groups in google_tech_client_condition_groups().items():
                    merged[scoped_answer_id(general_id, vlopse)].extend(
                        _scope_condition_groups(or_groups, vlopse)
                    )

        for general_id, or_groups in load_general_conditions().items():
            if general_id in covered:
                continue
            if general_id in COLLAB_STRUCTURED_SUPPLEMENT_IDS:
                if not collab_structured_required(mapped_all):
                    continue
            if (
                general_id in COLLAB_BASIC_FIELD_IDS
                and collab_structured_required(mapped_all)
            ):
                continue
            if (
                general_id in PURPOSE_LIMITATION_SUPPLEMENT_IDS
                and not purpose_limitation_relevant(mapped_all)
            ):
                continue
            if (
                general_id in COLLAB_SHARE_SUPPLEMENT_IDS
                and not collab_share_relevant(mapped_all)
            ):
                continue
            if general_condition_triggers(or_groups) & mapped_all:
                merged[general_id].extend(or_groups)

        return dict(merged)
