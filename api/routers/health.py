from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("", summary="Liveness probe")
def liveness():
    return JSONResponse({"status": "ok"})
