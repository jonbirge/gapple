from datetime import datetime

from sqlmodel import Field, SQLModel


class SyncPair(SQLModel, table=True):
    __tablename__ = "sync_pairs"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    icloud_calendar_id: int = Field(foreign_key="icloud_calendars.id")
    google_calendar_id: int = Field(foreign_key="google_calendars.id")
    preferred_side: str = "google"  # "icloud" or "google"
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
