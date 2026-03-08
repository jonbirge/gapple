from datetime import datetime

from sqlmodel import Field, SQLModel


class EventSnapshot(SQLModel, table=True):
    __tablename__ = "event_snapshots"

    id: int | None = Field(default=None, primary_key=True)
    sync_pair_id: int = Field(foreign_key="sync_pairs.id", index=True)
    event_uid: str
    google_event_id: str | None = None
    icloud_etag: str | None = None
    google_etag: str | None = None
    content_hash: str | None = None
    last_synced_at: datetime = Field(default_factory=datetime.utcnow)
