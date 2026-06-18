from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models import InputType


class DSAQuestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    text: str
    required: bool = True
    input_type: InputType
    help_text: str | None = None
    config: dict[str, Any] | None = None
    options: list[str] | None = None
    granularity: str = "general"
    source_general_id: str | None = None
    vlopse: str | None = None
    group_text: str | None = None
