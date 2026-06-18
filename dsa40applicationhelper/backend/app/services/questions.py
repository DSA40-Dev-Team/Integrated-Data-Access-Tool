from app.models import InputType
from app.services.question_store import (
    PlatformQuestionRecord,
    UnifiedQuestionRecord,
    find_platform_question_global,
    load_platform_questions,
    load_unified_questions,
    save_platform_questions,
    save_unified_questions,
)


class QuestionService:
    def add(
        self,
        id: str | None,
        text: str,
        vlopse: str,
        required: bool,
        input_type: str,
        details: str | None,
        config: dict[str, str] | None = None,
    ) -> None:
        records = load_platform_questions(vlopse)
        qid = id or ""
        if any(r.id == qid for r in records):
            raise ValueError(f"Duplicate platform question id: {qid}")
        records.append(
            PlatformQuestionRecord(
                id=qid,
                text=text,
                vlopse=vlopse,
                required=required,
                input_type=InputType(input_type),
                details=details,
                config=config,
            )
        )
        save_platform_questions(vlopse, records)

    def get_all_for_vlopse(self, vlopse: str) -> list[PlatformQuestionRecord]:
        return load_platform_questions(vlopse)

    def get(self, question_id: str) -> PlatformQuestionRecord | None:
        return find_platform_question_global(question_id)

    def add_unified(
        self,
        id: str | None,
        text: str,
        input_type: str,
        help_text: str | None,
        config: dict[str, str] | None = None,
    ) -> None:
        records = load_unified_questions()
        qid = id or ""
        if any(r.id == qid for r in records):
            raise ValueError(f"Duplicate unified question id: {qid}")
        records.append(
            UnifiedQuestionRecord(
                id=qid,
                text=text,
                input_type=InputType(input_type),
                help_text=help_text,
                config=config,
            )
        )
        save_unified_questions(records)

    def get_unified(self, question_id: str) -> UnifiedQuestionRecord | None:
        for record in load_unified_questions():
            if record.id == question_id:
                return record
        return None

    def get_all_unified_for(
        self, question_ids: list[str]
    ) -> list[UnifiedQuestionRecord]:
        wanted = set(question_ids)
        return [q for q in load_unified_questions() if q.id in wanted]

    def get_all_unified(self) -> list[UnifiedQuestionRecord]:
        return load_unified_questions()
