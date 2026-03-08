from datetime import datetime

from sqlmodel import Field, SQLModel


class GoogleCalendar(SQLModel, table=True):
    __tablename__ = "google_calendars"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    google_calendar_id: str
    display_name: str
    color: str | None = None
    last_discovered: datetime = Field(default_factory=datetime.utcnow)


class ICloudCalendar(SQLModel, table=True):
    __tablename__ = "icloud_calendars"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    caldav_url: str
    display_name: str
    color: str | None = None
    ctag: str | None = None
    last_discovered: datetime = Field(default_factory=datetime.utcnow)
