from fastapi import APIRouter
from pydantic import ValidationError
from sqlalchemy import text

from app.core.mapping import MappingValidationError, QuestionMapper
from app.database import SessionLocal
from app.services.form_engine import FormService
from app.services.questions import QuestionService
from app.services.vlopse import VlopseConfigService

from .schemas.health import HealthResponse, Status

question_service = QuestionService()
form_service = FormService()
vlopse_service = VlopseConfigService()
router = APIRouter()


@router.get("/health")
def health_check() -> HealthResponse:
    db = SessionLocal()
    db_status = Status.ERROR
    dsa_status = Status.ERROR
    mapping_status = Status.ERROR
    try:
        questions = question_service.get_all_unified()
        dsa_status = len(questions)
        vlopses = vlopse_service.get_all()
        for vlopse in vlopses:
            try:
                _is_it_loadable = vlopse_service.get(vlopse)
            except ValidationError as e:
                print(f"INVALID VLOPSE CONFIG FOR {vlopse}")
                print(f"REASON: {e}")
        mapper = QuestionMapper.from_vlopse_names(vlopses, question_service)
        mapper._validate()
        mapping_status = Status.OK
        db.execute(text("SELECT 1"))
        db_status = Status.OK
    except MappingValidationError as e:
        print(f"ERROR {e}")
    except Exception as e:
        print(f"ERROR {e}")

    finally:
        db.close()
    return HealthResponse(
        api=Status.OK,
        db=db_status,
        dsa_status=dsa_status,
        mapping_status=mapping_status,
    )
