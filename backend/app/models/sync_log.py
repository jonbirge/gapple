from datetime import datetime

from sqlmodel import Field, SQLModel


class SyncLog(SQLModel, table=True):
    __tablename__ = "sync_logs"

    id: int | None = Field(default=None, primary_key=True)
    sync_pair_id: int = Field(foreign_key="sync_pairs.id", index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    status: str = "error"  # "success", "partial", or "error"
    events_created: int = 0
    events_updated: int = 0
    events_deleted: int = 0
    conflicts_resolved: int = 0
    error_details: str | None = None
