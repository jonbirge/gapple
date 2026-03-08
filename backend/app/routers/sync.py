from fastapi import APIRouter

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.get("/status")
async def sync_status():
    return {"status": "not implemented"}
