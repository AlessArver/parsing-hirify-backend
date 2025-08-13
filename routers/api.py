from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from services.vacancy_service import get_filtered_vacancies

router = APIRouter()


@router.get("/parse-vacancies")
async def parse_vacancies(
    page: int = Query(1),
    grade: Optional[str] = Query(None),
    specializations: Optional[str] = Query(None),
    vacancy_language: Optional[str] = Query(None),
):
    try:
        filters = {
            "grade": grade,
            "specializations": specializations,
            "vacancy_language": vacancy_language,
        }
        return await get_filtered_vacancies(filters, page)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
