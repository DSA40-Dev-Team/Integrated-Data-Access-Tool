import pathlib
import re
from typing import Annotated, Literal, Union

from pycountry import countries
from pydantic import BaseModel, Field, TypeAdapter

_ORCID_PATTERN = re.compile(
    r"^(?:https?://orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$",
    re.IGNORECASE,
)


def _orcid_checksum_valid(orcid: str) -> bool:
    digits = orcid.replace("-", "")
    total = 0
    for digit in digits[:-1]:
        total = (total + int(digit)) * 2
    remainder = total % 11
    check = (12 - remainder) % 11
    expected = "X" if check == 10 else str(check)
    return digits[-1].upper() == expected


class ISO_3166_1(BaseModel):
    type: Literal["iso-3166-1"]

    def validate_answer(self, value: str) -> str | None:
        country = countries.get(name=value)
        if country is None:
            return f"Invalid selection: {value}"
        return None


class Selection(BaseModel):
    # TODO: rename property name
    type: Literal["selection"]
    options: list[str]
    multiple: bool = False

    def validate_answer(self, value: str | list[str]) -> str | None:
        if isinstance(value, list) and not self.multiple:
            return "Only one selection allowed"
        values = value if isinstance(value, list) else [value]
        invalid = [v for v in values if v not in self.options]
        if invalid:
            return f"Invalid option(s): {', '.join(invalid)}. Possible: {', '.join(self.options)}"
        return None


class MultiSelect(BaseModel):
    type: Literal["multi_select"]
    options: list[str] = Field(default_factory=list)

    def validate_answer(self, value: str | list[str]) -> str | None:
        if value is None or (isinstance(value, str) and not str(value).strip()):
            return None
        if isinstance(value, list):
            values = [str(v).strip() for v in value if str(v).strip()]
        elif "; " in value:
            values = [part.strip() for part in value.split("; ") if part.strip()]
        else:
            values = [part.strip() for part in value.split(";") if part.strip()]
        if self.options:
            invalid = [v for v in values if v not in self.options]
            if invalid:
                return (
                    f"Invalid option(s): {', '.join(invalid)}. "
                    f"Possible: {', '.join(self.options)}"
                )
        return None


class Boolean(BaseModel):
    type: Literal["boolean"]

    def validate_answer(self, value: str) -> str | None:
        if value.lower() not in ["yes", "no", "true", "false"]:
            return f"Invalid boolean {value}"
        return None


class Text(BaseModel):
    type: Literal["text"]
    max_length: int | None = None
    multiline: bool = False
    rows: int = 4

    def validate_answer(self, value: str) -> str | None:
        if self.max_length and len(value) > self.max_length:
            return f"Must not exceed {self.max_length} characters"
        return None


class Orcid(BaseModel):
    type: Literal["orcid"]

    def validate_answer(self, value: str) -> str | None:
        if not value.strip():
            return None
        match = _ORCID_PATTERN.match(value.strip())
        if match is None:
            return (
                "Invalid ORCID iD. Expected format: 0000-0002-1825-0097 "
                "(optional https://orcid.org/ prefix)."
            )
        if not _orcid_checksum_valid(match.group(1)):
            return "Invalid ORCID iD checksum."
        return None


class FileUpload(BaseModel):
    type: Literal["file_upload"]

    def validate_answer(self, value: str) -> str | None:
        try:
            p = pathlib.Path(value)
            if not p.name:
                return f"{value} does not look like a file name."

        except ValueError:
            return f"{value} does not look like a file name."
        return None


class DateRange(BaseModel):
    type: Literal["daterange"]
    begin: Literal["TODO"]


class DateSelect(BaseModel):
    type: Literal["date_select"]


ConstraintConfig = Annotated[
    Union[Selection, MultiSelect, Text, ISO_3166_1, Orcid], Field(discriminator="type")
]


config_adapter = TypeAdapter(ConstraintConfig)
