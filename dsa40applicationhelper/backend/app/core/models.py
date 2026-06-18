from enum import Enum
from typing import Literal

from pydantic import BaseModel

from app.models import InputType
from app.schemas import ConstraintConfig, config_adapter


class PlatformMappingComplex(BaseModel):
    operation: str
    src: str | list[str] | None = None
    value: str | None = None


PlatformMapping = str | PlatformMappingComplex


class VlopseAnswer(BaseModel):
    id: str
    value: str


class Answer(BaseModel):
    question_id: str
    value: str | None


class MappingResult(BaseModel):
    question_id: str


class MappedAnswer(MappingResult):
    type: Literal["result"] = "result"
    value: str


class ErrorDetails(BaseModel):
    type: Literal["type_error", "value_error"]
    loc: list[str]
    message: str


class MappingError(MappingResult):
    type: Literal["error"] = "error"
    errors: list[ErrorDetails]


class WithText(MappingError, MappingResult):
    text: str


class UnifiedQuestion(BaseModel):
    id: str
    text_en: str
    required: bool
    type: InputType
    help_text: str | None = None
    config: ConstraintConfig | None = None

    @property
    def parsed_config(self) -> ConstraintConfig | None:
        return self.config
        if self.config:
            # TODO: reintroduced once this goes into the db
            return config_adapter.validate_python(self.config)


# class InputType(str, Enum):
#     text = "text"
#     file_upload = "file_upload"
#     date_select = "date_select"
#     selection = "selection"
#     multi_select = "multi_select"
# @computed_field
# def input_type(self):
#     match self.type:
#         case InputType.text:
#             ...
#         case InputType.file_upload:
#             ...
#         case InputType.date_select:
#             ...
#         case InputType.selection:
#             ...
#         case InputType.multi_select:
#             ...


class Operator(str, Enum):
    eq = "eq"
    neq = "neq"


class Condition(BaseModel):
    question_id: str
    operator: Operator
    value: str
