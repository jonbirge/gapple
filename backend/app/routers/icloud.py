from fastapi import APIRouter

router = APIRouter(prefix="/api/icloud", tags=["icloud"])


@router.get("/status")
async def icloud_status():
    return {"status": "not implemented"}
