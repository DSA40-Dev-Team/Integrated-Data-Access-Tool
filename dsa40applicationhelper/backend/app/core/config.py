from enum import Enum
import json
from pathlib import Path

from pydantic import BaseModel

from .models import Condition, PlatformMapping

_VLOPSE_CONFIG_DIR = Path(__file__).parent.parent / "data" / "vlopses"


class ApplicationModality(str, Enum):
    form = "form"
    email = "email"


class PlatformDisclaimerLink(BaseModel):
    label: str
    url: str


class PlatformDisclaimer(BaseModel):
    """Legal or contractual text the platform form requires; shown as a disclaimer in the helper."""

    id: str
    text: str
    highlights: list[str] = []
    links: list[PlatformDisclaimerLink] = []


class PlatformInformation(BaseModel):
    name: str
    platform_information: str | None = None
    account_required: bool
    application_link: str
    modality: ApplicationModality
    disclaimers: list[PlatformDisclaimer] = []
    term_implications: list[str] = []


class VLOPSEConfiguration(BaseModel):
    info: PlatformInformation
    mappings: dict[str, PlatformMapping]
    conditions: dict[str, list[Condition]]


def _load_json(filename: str) -> VLOPSEConfiguration:
    from app.core.conditions_util import normalize_stored_conditions

    path = _VLOPSE_CONFIG_DIR / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data.get("conditions"), dict):
        normalized = normalize_stored_conditions(data["conditions"])
        data["conditions"] = {
            key: [clause.model_dump() for clause in clauses]
            for key, clauses in normalized.items()
        }
    return VLOPSEConfiguration.model_validate(data)


def _write_json(filename: str, value: VLOPSEConfiguration):
    path = _VLOPSE_CONFIG_DIR / filename
    serialized = value.model_dump_json()
    with open(path, "w") as f:
        f.write(serialized)


def get_vlopse_configuration_for(platform_name: str) -> VLOPSEConfiguration:
    return _load_json(f"{platform_name}.json")


def write_vlopse_configuration_for(platform_name: str, config: VLOPSEConfiguration):
    return _write_json(f"{platform_name}.json", config)
