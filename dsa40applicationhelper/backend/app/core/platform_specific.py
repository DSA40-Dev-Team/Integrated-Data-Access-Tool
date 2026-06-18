"""Helpers for per-platform general question answers."""

from __future__ import annotations

ANSWER_KEY_SEP = "__"


def scoped_answer_id(general_id: str, vlopse: str) -> str:
    return f"{general_id}{ANSWER_KEY_SEP}{vlopse}"


def general_ids_from_mapping_value(mapping_value: object) -> list[str]:
    from app.core.conditions_util import general_ids_from_mapping

    return general_ids_from_mapping(mapping_value)  # type: ignore[arg-type]


def vlopse_maps_to_general(vlopse: str, general_id: str) -> bool:
    from app.core.config import get_vlopse_configuration_for

    config = get_vlopse_configuration_for(vlopse)
    for mapping in config.mappings.values():
        if general_id in general_ids_from_mapping_value(mapping):
            return True
    return False


def vlopses_mapping_general(vlopses: list[str], general_id: str) -> list[str]:
    return [vlopse for vlopse in vlopses if vlopse_maps_to_general(vlopse, general_id)]


def is_platform_specific_general(general_id: str) -> bool:
    from app.core.conditions_util import granularity_for_general

    base = general_id.split(ANSWER_KEY_SEP, 1)[0]
    return granularity_for_general(base) == "platform_specific"


def platform_specific_general_ids() -> frozenset[str]:
    from app.services.question_store import load_unified_questions

    return frozenset(
        record.id
        for record in load_unified_questions()
        if (record.granularity or "general") == "platform_specific"
    )


def format_platform_placeholder(text: str, platform_names: list[str]) -> str:
    """Replace ``<PLATFORM_NAME>`` with one name or ``the platforms``."""
    if "<PLATFORM_NAME>" not in text:
        return text
    replacement = platform_names[0] if len(platform_names) == 1 else "the platforms"
    return text.replace("<PLATFORM_NAME>", replacement)


META_DATA_REQUESTED_HELP = (
    "For more information about the available data types, see the product "
    "documentation for MCL: "
    "https://developers.facebook.com/docs/content-library-and-api"
)
