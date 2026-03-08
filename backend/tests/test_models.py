from datetime import datetime

import pytest
from sqlmodel import select

from app.models import (
    EventSnapshot,
    GoogleCalendar,
    GoogleCredential,
    ICloudCalendar,
    ICloudCredential,
    SyncLog,
    SyncPair,
    User,
)


async def _create_user(session, sub="u1") -> int:
    """Helper: create a user and return its id."""
    user = User(google_sub=sub, email=f"{sub}@example.com")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user.id


async def _create_calendars(session, user_id: int) -> tuple[int, int]:
    """Helper: create an iCloud + Google calendar pair and return their ids."""
    ic = ICloudCalendar(user_id=user_id, caldav_url=f"https://ic/{user_id}", display_name="ic")
    gc = GoogleCalendar(user_id=user_id, google_calendar_id=f"gc-{user_id}", display_name="gc")
    session.add(ic)
    session.add(gc)
    await session.commit()
    await session.refresh(ic)
    await session.refresh(gc)
    return ic.id, gc.id


async def _create_sync_pair(session, user_id: int, ic_id: int, gc_id: int) -> int:
    pair = SyncPair(
        user_id=user_id, icloud_calendar_id=ic_id, google_calendar_id=gc_id
    )
    session.add(pair)
    await session.commit()
    await session.refresh(pair)
    return pair.id


@pytest.mark.asyncio
async def test_create_user(async_session):
    user = User(google_sub="abc123", email="test@example.com", display_name="Test User")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    assert user.id is not None
    result = await async_session.exec(select(User).where(User.google_sub == "abc123"))
    fetched = result.one()
    assert fetched.email == "test@example.com"


@pytest.mark.asyncio
async def test_create_google_credential(async_session):
    user_id = await _create_user(async_session, "gcred")

    cred = GoogleCredential(
        user_id=user_id,
        encrypted_access_token="enc_access",
        encrypted_refresh_token="enc_refresh",
        token_expiry=datetime(2026, 12, 31),
        scopes="calendar",
    )
    async_session.add(cred)
    await async_session.commit()
    await async_session.refresh(cred)

    assert cred.id is not None
    assert cred.user_id == user_id


@pytest.mark.asyncio
async def test_create_icloud_credential(async_session):
    user_id = await _create_user(async_session, "iccred")

    cred = ICloudCredential(
        user_id=user_id,
        apple_id_email="apple@icloud.com",
        encrypted_app_specific_password="enc_pass",
    )
    async_session.add(cred)
    await async_session.commit()
    await async_session.refresh(cred)

    assert cred.id is not None
    assert cred.caldav_principal_url is None


@pytest.mark.asyncio
async def test_create_google_calendar(async_session):
    user_id = await _create_user(async_session, "gcal")

    cal = GoogleCalendar(
        user_id=user_id,
        google_calendar_id="cal123@google.com",
        display_name="My Calendar",
        color="#0000ff",
    )
    async_session.add(cal)
    await async_session.commit()
    await async_session.refresh(cal)

    assert cal.id is not None


@pytest.mark.asyncio
async def test_create_icloud_calendar(async_session):
    user_id = await _create_user(async_session, "iccal")

    cal = ICloudCalendar(
        user_id=user_id,
        caldav_url="https://caldav.icloud.com/12345/calendars/abc/",
        display_name="Family",
    )
    async_session.add(cal)
    await async_session.commit()
    await async_session.refresh(cal)

    assert cal.id is not None


@pytest.mark.asyncio
async def test_create_sync_pair(async_session):
    user_id = await _create_user(async_session, "sp")
    ic_id, gc_id = await _create_calendars(async_session, user_id)

    pair = SyncPair(
        user_id=user_id,
        icloud_calendar_id=ic_id,
        google_calendar_id=gc_id,
        preferred_side="icloud",
    )
    async_session.add(pair)
    await async_session.commit()
    await async_session.refresh(pair)

    assert pair.id is not None
    assert pair.enabled is True


@pytest.mark.asyncio
async def test_create_event_snapshot(async_session):
    user_id = await _create_user(async_session, "es")
    ic_id, gc_id = await _create_calendars(async_session, user_id)
    pair_id = await _create_sync_pair(async_session, user_id, ic_id, gc_id)

    snap = EventSnapshot(
        sync_pair_id=pair_id,
        event_uid="uid-abc-123",
        google_event_id="gevt123",
        content_hash="sha256:abc",
    )
    async_session.add(snap)
    await async_session.commit()
    await async_session.refresh(snap)

    assert snap.id is not None
    assert snap.event_uid == "uid-abc-123"


@pytest.mark.asyncio
async def test_create_sync_log(async_session):
    user_id = await _create_user(async_session, "sl")
    ic_id, gc_id = await _create_calendars(async_session, user_id)
    pair_id = await _create_sync_pair(async_session, user_id, ic_id, gc_id)

    log = SyncLog(
        sync_pair_id=pair_id,
        status="success",
        events_created=5,
        events_updated=2,
        events_deleted=1,
        conflicts_resolved=0,
        completed_at=datetime.utcnow(),
    )
    async_session.add(log)
    await async_session.commit()
    await async_session.refresh(log)

    assert log.id is not None
    assert log.events_created == 5
