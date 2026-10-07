from enum import StrEnum
from typing import TYPE_CHECKING

from django.db import connection
from django.db.utils import Error as DjangoDatabaseError
from ninja import Router, Schema

if TYPE_CHECKING:
    from django.http import HttpRequest

router = Router()


class Status(StrEnum):
    OK = "ok"
    ERROR = "error"


class HealthOut(Schema):
    api: Status
    db: Status
    dsa_status: int | Status
    mapping_status: int | Status


@router.get("", response=HealthOut)
def health_check(request: HttpRequest) -> HealthOut:
    """Report API liveness and DB connectivity."""
    db_status = Status.OK
    dsa_status = Status.ERROR  # TODO: Count number of DSA questions
    mapping_status = Status.ERROR  # TODO: Call validate on Mapper
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DjangoDatabaseError:
        db_status = Status.ERROR

    return HealthOut(
        api=Status.OK,
        db=db_status,
        dsa_status=dsa_status,
        mapping_status=mapping_status,
    )
