from fastapi import APIRouter

router = APIRouter(prefix="/api/calendars", tags=["calendars"])


@router.get("/")
async def list_calendars():
    return {"status": "not implemented"}
