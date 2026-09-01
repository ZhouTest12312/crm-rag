from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from config.db_conf import get_database
from crud.classes import list_classes, list_classes_detail

router = APIRouter(prefix="/api/classes", tags=["classes"])


@router.get("/list")
async def get_classes(db=Depends(get_database)):
    rows = await list_classes(db)
    if not rows:
        return JSONResponse(content={"code": 404, "msg": "查询失败", "data": None})
    return {
        "code": "200",
        "msg": "success",
        "data": {
            "count": len(rows),
            "classes": [
                {
                    "id": r.id,
                    "name": r.name,
                    "subject": r.subject,
                    "teacher_name": r.teacher_name,
                    "status": r.status,
                    "enrolled_count": r.enrolled_count,
                }
                for r in rows
            ],
        },
    }


@router.get("/detail/{id}")
async def get_classes_detail(id: str, db=Depends(get_database)):
    raw = await list_classes_detail(db, id)
    if not raw:
        return JSONResponse(content={"code": 404, "msg": "查询失败", "data": None})
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "id": raw.id,
            "name": raw.name,
            "subject": raw.subject,
            "teacher_name": raw.teacher_name,
            "status": raw.status,
            "enrolled_count": raw.enrolled_count,
        },
    }
