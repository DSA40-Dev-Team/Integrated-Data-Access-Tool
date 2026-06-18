from enum import Enum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.schemas import ConstraintConfig, config_adapter


class InputType(str, Enum):
    text = "text"
    file_upload = "file_upload"
    date_select = "date_select"
    selection = "selection"
    multi_select = "multi_select"
    ISO_3166_1 = "iso-3166-1"
    orcid = "orcid"
    repeatable_group = "repeatable_group"
    composite_group = "composite_group"


class Base(DeclarativeBase):
    pass


class ReprMixing:
    def __repr__(self) -> str:
        return self._repr(id=self.id)

    def _repr(self, **fields: dict[str, Any]) -> str:
        """
        Helper for __repr__
        """
        field_strings = []
        at_least_one_attached_attribute = False
        for key, field in fields.items():
            try:
                field_strings.append(f"{key}={field!r}")
            except sa.orm.exc.DetachedInstanceError:
                field_strings.append(f"{key}=DetachedInstanceError")
            else:
                at_least_one_attached_attribute = True
        if at_least_one_attached_attribute:
            return f"<{self.__class__.__name__}({','.join(field_strings)})>"
        return f"<{self.__class__.__name__} {id(self)}>"


class VLOPSEQuestion(Base, ReprMixing):
    __tablename__ = "vlopse_question"
    id = Column(String, primary_key=True, index=True)
    text = Column(Text)
    vlopse = Column(String(255))
    required = Column(Boolean)
    input_type = Column(SQLAlchemyEnum(InputType))
    details = Column(Text, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    def __repr__(self):
        # easy to override, and it'll honor __repr__ in foreign relationships
        return self._repr(
            id=self.id,
            text=self.text,
            vlopse=self.vlopse,
            required=self.required,
            details=self.details,
            options=self.config,
        )


class DSAQuestion(Base, ReprMixing):
    __tablename__ = "dsa_question"
    id = Column(String, primary_key=True, index=True)
    text = Column(Text)
    help_text = Column(Text, nullable=True)
    input_type = Column(SQLAlchemyEnum(InputType))
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    def __repr__(self):
        # easy to override, and it'll honor __repr__ in foreign relationships
        return self._repr(
            id=self.id,
            text=self.text,
            input_type=self.input_type,
            config=self.config,
            help_text=self.help_text,
        )

    @property
    def parsed_config(self) -> ConstraintConfig | None:
        if self.config:
            return config_adapter.validate_python(self.config)
