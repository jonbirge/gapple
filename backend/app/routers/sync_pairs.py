from fastapi import APIRouter

router = APIRouter(prefix="/api/sync-pairs", tags=["sync-pairs"])


@router.get("/")
async def list_sync_pairs():
    return {"status": "not implemented"}
