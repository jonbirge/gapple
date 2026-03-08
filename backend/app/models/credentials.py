from datetime import datetime

from sqlmodel import Field, SQLModel


class GoogleCredential(SQLModel, table=True):
    __tablename__ = "google_credentials"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    encrypted_access_token: str
    encrypted_refresh_token: str
    token_expiry: datetime | None = None
    scopes: str = ""


class ICloudCredential(SQLModel, table=True):
    __tablename__ = "icloud_credentials"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    apple_id_email: str
    encrypted_app_specific_password: str
    caldav_principal_url: str | None = None
