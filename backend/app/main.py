import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import create_db_and_tables
from app.routers import auth, calendars, icloud, sync, sync_pairs


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the data directory exists for SQLite
    db_dir = Path("./data")
    db_dir.mkdir(parents=True, exist_ok=True)
    await create_db_and_tables()
    yield


app = FastAPI(title="Gapple", version="0.1.0", lifespan=lifespan)

# Include routers
app.include_router(auth.router)
app.include_router(calendars.router)
app.include_router(sync_pairs.router)
app.include_router(sync.router)
app.include_router(icloud.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


# Mount frontend static files if the dist directory exists
_static_dir = Path(os.environ.get("GAPPLE_STATIC_DIR", ""))
if not _static_dir.is_dir():
    _static_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="frontend")
