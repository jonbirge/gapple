# CLAUDE.md — Gapple

> Gapple is a web application that syncs calendars between Apple iCloud and Google Calendar. It solves the problem of Android users in families that share iCloud calendars by providing bidirectional, manual sync between paired calendars from each service.

---

## Architecture Overview

Gapple is a self-hosted, multi-user web application deployed as a single Docker container via Docker Compose on a Linux VPS.

- **Backend:** Python 3.12+ with FastAPI (async)
- **Frontend:** Vue 3 + Vuetify 3 (TypeScript, relaxed strict mode)
- **Database:** SQLite via SQLModel ORM, Alembic migrations
- **Deployment:** Single container — FastAPI serves the Vue frontend as static files built at Docker image build time

### Monorepo Structure

```
gapple/
├── CLAUDE.md
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point, static file serving
│   │   ├── config.py            # Settings from environment variables
│   │   ├── database.py          # SQLite engine, session management
│   │   ├── models/              # SQLModel table definitions
│   │   │   ├── user.py
│   │   │   ├── credentials.py   # Google OAuth tokens + iCloud credentials
│   │   │   ├── calendar.py      # Discovered calendars on both sides
│   │   │   ├── sync_pair.py
│   │   │   ├── event_snapshot.py
│   │   │   └── sync_log.py
│   │   ├── routers/             # FastAPI route modules
│   │   │   ├── auth.py          # Google OAuth login flow
│   │   │   ├── calendars.py     # Calendar discovery and listing
│   │   │   ├── sync_pairs.py    # CRUD for sync pair configuration
│   │   │   ├── sync.py          # Trigger sync, retrieve sync logs
│   │   │   └── icloud.py        # iCloud credential management
│   │   ├── services/            # Business logic layer
│   │   │   ├── google_calendar.py
│   │   │   ├── icloud_caldav.py
│   │   │   ├── sync_engine.py   # Core bidirectional diff + sync logic
│   │   │   ├── event_mapper.py  # iCal <-> Google event field mapping
│   │   │   └── encryption.py    # Fernet encrypt/decrypt for credentials
│   │   └── utils/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_sync_engine.py
│   │   ├── test_event_mapper.py
│   │   ├── test_calendars.py
│   │   └── test_encryption.py
│   ├── alembic/
│   │   └── versions/
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   ├── router/
│   │   ├── components/
│   │   ├── views/
│   │   ├── composables/         # Vue 3 composition API hooks
│   │   ├── types/               # TypeScript interfaces mirroring API models
│   │   └── api/                 # API client functions
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
```

---

## Core Concepts

### Authentication

**App login:** Google OAuth only. Users authenticate with their Google account. This serves dual purpose — it establishes their app identity AND obtains Google Calendar API access (access token + refresh token). Open registration; any Google account can create a Gapple account. Email verification is handled implicitly by Google OAuth (Google accounts have verified emails).

**iCloud access:** Users provide their Apple ID email and an app-specific password (NOT their real Apple ID password). The app uses these as HTTP Basic Auth credentials against Apple's CalDAV endpoints at `caldav.icloud.com`. The UI must prominently instruct users on how to generate an app-specific password and explain why it's necessary.

**Credential storage:** All sensitive credentials (Google OAuth tokens, iCloud app-specific passwords) are encrypted at rest using Fernet symmetric encryption from Python's `cryptography` library. The Fernet key is derived from a server-managed secret stored in the `.env` file.

> **Future consideration:** A user-provided vault passphrase (Option B) could be layered on top for higher security. The encryption service should be designed to allow swapping the key source without changing the rest of the application.

### Sync Engine

The sync engine is the core of the application. It operates on **sync pairs** — user-defined pairings of one iCloud calendar with one Google calendar.

**Sync is manual only.** Users click a "Sync Now" button per pair in the UI. There is no scheduled or automatic syncing.

**Sync is bidirectional.** Changes on either side propagate to the other.

**Sync is diff-based.** The engine maintains an `event_snapshots` table that stores the last-known state (UID + etag/content hash) of every event in each sync pair, on each side. On each sync run:

1. Fetch all future events from both the iCloud calendar (CalDAV REPORT) and the Google calendar (Events.list API).
2. Compare each side's current state against the stored snapshots.
3. Classify every event as: unchanged, created (new), modified, or deleted — independently for each side.
4. For events changed on only one side: propagate the change to the other side.
5. For events changed on both sides (conflict): the **preferred side wins**. Each sync pair has a `preferred_side` field (`icloud` or `google`) set by the user.
6. For events deleted on one side: **propagate the deletion** to the other side.
7. Update the snapshots table to reflect the new state.
8. Write a sync log entry with counts (created, updated, deleted, conflicted) and any errors.

**Time range:** Only future events are synced. Events in the past are ignored. The cutoff is the current timestamp at sync execution time.

**Event fields synced:** All standard calendar event fields are mapped between iCal (RFC 5545) and Google Calendar API format:
- Summary / title
- Start and end time (with timezone handling)
- Location
- Description
- Recurrence rules (RRULE)
- Alerts / reminders

The `event_mapper.py` service handles bidirectional translation between iCal VEVENT properties and Google Calendar event resource fields.

> **⚠️ Known complexity: Recurrence rules.** Mapping RRULE between iCal and Google's recurrence format is one of the hardest parts of this project. Google uses a subset of RFC 5545 RRULE but represents exceptions differently (via `recurringEventId` + individual modified instances). The event mapper must handle: basic RRULE translation, recurrence exceptions (EXDATE), modified instances of recurring events, and the conceptual mismatch between CalDAV's monolithic VCALENDAR (with VEVENT + overrides in one object) and Google's split representation. Expect edge cases. Write thorough tests for this module.

### Event Identity

Events are tracked across systems using the iCal `UID` property as the stable identifier. When an event is first synced from one side to the other, the mapping between the iCal UID and the Google event ID is recorded in the snapshots table. This mapping is essential for subsequent syncs to recognize that an event on one side corresponds to an event on the other.

---

## Database Schema

Seven tables, defined as SQLModel models:

| Table | Purpose |
|---|---|
| `users` | Google OAuth identity: google_sub, email, display_name, created_at, last_login |
| `google_credentials` | Per-user: encrypted access_token, encrypted refresh_token, token_expiry, scopes |
| `icloud_credentials` | Per-user: apple_id_email, encrypted app_specific_password, caldav_principal_url (cached after discovery) |
| `google_calendars` | Discovered Google calendars: user_id, google_calendar_id, display_name, color, last_discovered |
| `icloud_calendars` | Discovered iCloud calendars: user_id, caldav_url, display_name, color/ctag, last_discovered |
| `sync_pairs` | User-defined pairings: user_id, icloud_calendar_id, google_calendar_id, preferred_side (enum: icloud/google), enabled, created_at |
| `event_snapshots` | Diff tracking: sync_pair_id, event_uid, google_event_id, icloud_etag, google_etag, content_hash, last_synced_at |
| `sync_logs` | Sync history: sync_pair_id, started_at, completed_at, status (success/partial/error), events_created, events_updated, events_deleted, conflicts_resolved, error_details |

Migrations managed by Alembic. Generate with `alembic revision --autogenerate -m "description"`, apply with `alembic upgrade head`.

---

## API Integration Details

### Google Calendar API

- Library: `google-api-python-client` + `google-auth` + `google-auth-oauthlib`
- Auth: OAuth 2.0 with offline access (to obtain refresh token)
- Scopes: `https://www.googleapis.com/auth/calendar` (read/write)
- Token refresh: handled automatically by the google-auth library; persist updated tokens after refresh
- Key endpoints used: `CalendarList.list` (discovery), `Events.list` (with `timeMin` for future events), `Events.insert`, `Events.update`, `Events.delete`
- Google OAuth client ID and secret stored in `.env`

### iCloud CalDAV

- Library: `caldav` (Python CalDAV client library) + `icalendar` (for VEVENT parsing/construction)
- Auth: HTTP Basic Auth with Apple ID email + app-specific password
- Server: `https://caldav.icloud.com/`
- Discovery: CalDAV principal lookup → calendar-home-set → individual calendars
- Operations: `PROPFIND` (discover calendars, get ctags/etags), `REPORT` with `calendar-query` or `calendar-multiget` (fetch events), `PUT` (create/update events), `DELETE` (delete events)
- Apple does not document their CalDAV implementation publicly. Expect some endpoint discovery quirks. The `caldav` library handles most of the protocol-level details.

> **Note:** iCloud CalDAV can be flaky — timeouts, intermittent 5xx errors. The sync engine should implement retry with backoff for CalDAV operations.

---

## Frontend

### Stack

- Vue 3 with Composition API (`<script setup>`)
- Vuetify 3 for all UI components (Material Design)
- TypeScript in relaxed mode (`strict: false` in tsconfig) — use types for API response interfaces and component props; don't fight the type system for internal logic
- Vite for build tooling
- Built to static files (`npm run build`) and served by FastAPI via `StaticFiles` mount

### Design

Clean and minimal aesthetic. Generous whitespace. Content organized in Vuetify cards. No dense data tables unless viewing sync logs.

### Key Views

- **Login page:** Google Sign-In button, brief explanation of what Gapple does
- **Dashboard:** List of configured sync pairs as cards, each with sync status, last synced time, and a "Sync Now" button
- **Add/Edit Sync Pair:** Select an iCloud calendar and a Google calendar from dropdowns, choose preferred side for conflicts
- **iCloud Setup:** Form to enter Apple ID email + app-specific password, with clear instructions on generating an app-specific password
- **Sync Log Viewer:** Summary shown by default (created/updated/deleted/conflicted counts), expandable to a detailed event-level log
- **Settings:** Account info, manage connected iCloud credentials, re-authorize Google if needed

### API Client

All API calls go through a centralized client module (`frontend/src/api/`) that handles auth headers (JWT or session cookie from Google OAuth), error handling, and response typing.

---

## Security Considerations

- **Never store real Apple ID passwords.** The UI must make clear that only app-specific passwords are accepted and guide users through creating one.
- **Fernet encryption** for all stored credentials (Google tokens, iCloud passwords). Key sourced from `GAPPLE_ENCRYPTION_KEY` in `.env`.
- **HTTPS required in production.** The app itself doesn't terminate TLS — use a reverse proxy (nginx, Caddy, Traefik) in front of it.
- **Google OAuth state parameter** must be validated to prevent CSRF.
- **No credential logging.** Ensure that credentials, tokens, and app-specific passwords never appear in logs, error messages, or API responses.
- **SQLite file permissions:** The database file should be readable only by the application user (chmod 600).

---

## Environment Variables

Defined in `.env` (see `.env.example` for template):

```
# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Encryption
GAPPLE_ENCRYPTION_KEY=          # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# App
GAPPLE_BASE_URL=http://localhost:8000
GAPPLE_DB_PATH=./data/gapple.db
GAPPLE_LOG_LEVEL=info
```

---

## Docker

### Dockerfile (multi-stage)

1. **Stage 1 (frontend build):** Node image, `npm install`, `npm run build` → produces `dist/`
2. **Stage 2 (runtime):** Python image, install Python dependencies, copy backend code, copy `dist/` from stage 1 into a location FastAPI serves as static files

### docker-compose.yml

Single service. Mounts a volume for the SQLite database (`./data:/app/data`). Reads `.env` file for configuration. Exposes one port (e.g., 8000).

---

## Testing

### Backend

- **Framework:** pytest + pytest-asyncio + httpx (for async FastAPI test client)
- **Coverage target:** High — all API endpoints and sync logic must have tests
- **Key test areas:**
  - Auth flow (Google OAuth callback, token storage, session management)
  - iCloud credential encryption/decryption round-trip
  - Sync engine: created/modified/deleted detection for each side
  - Sync engine: conflict resolution (preferred side wins)
  - Sync engine: deletion propagation
  - Event mapper: iCal ↔ Google field translation, especially recurrence rules
  - API endpoints: CRUD for sync pairs, calendar discovery, sync trigger
- **Mocking:** Mock external API calls (Google Calendar API, iCloud CalDAV) in tests. Use recorded responses where possible. Never hit real APIs in CI.
- Run tests: `cd backend && pytest`

### Frontend

- No frontend testing framework specified initially. Add Vitest if/when frontend logic becomes complex enough to warrant it.

---

## Development Workflow

### Local Development

1. Clone the repo
2. Backend: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`
3. Frontend: `cd frontend && npm install && npm run dev` (Vite dev server with proxy to backend)
4. Copy `.env.example` to `.env` and fill in Google OAuth credentials + generate a Fernet key

### Linting & Formatting

- **Python:** Ruff for linting and formatting. Configuration in `pyproject.toml`.
  - Run: `ruff check backend/` and `ruff format backend/`
- **Frontend:** ESLint + Prettier (standard Vue 3 + TypeScript config via `create-vue` scaffolding)

### Git Conventions

- Freeform but descriptive commit messages. Write what changed and why.
- No strict branch naming convention, but use feature branches for non-trivial work.

### Database Migrations

- After changing any SQLModel model: `cd backend && alembic revision --autogenerate -m "describe the change"`
- Review the generated migration before applying
- Apply: `alembic upgrade head`
- The SQLite database file lives at the path specified by `GAPPLE_DB_PATH`

---

## Key Libraries

### Backend (Python)

| Library | Purpose |
|---|---|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `sqlmodel` | ORM (SQLAlchemy + Pydantic) |
| `alembic` | Database migrations |
| `aiosqlite` | Async SQLite driver |
| `cryptography` | Fernet encryption for credentials |
| `caldav` | CalDAV client for iCloud |
| `icalendar` | iCal VEVENT parsing and construction |
| `google-api-python-client` | Google Calendar API client |
| `google-auth` / `google-auth-oauthlib` | Google OAuth 2.0 |
| `httpx` | HTTP client (used internally + in tests) |
| `pytest` / `pytest-asyncio` | Testing |
| `ruff` | Linting and formatting |

### Frontend (JavaScript/TypeScript)

| Library | Purpose |
|---|---|
| `vue` (3.x) | UI framework |
| `vuetify` (3.x) | Material Design component library |
| `vue-router` | Client-side routing |
| `vite` | Build tool and dev server |
| `typescript` | Type checking (relaxed strict mode) |

---

## Future Considerations

Items explicitly deferred from v1:

- **Automatic/scheduled sync** — run syncs on a cron interval per pair. Would require a background task runner (e.g., `apscheduler`, Celery, or a simple asyncio loop).
- **User-provided vault passphrase** (Option B encryption) — layered on top of Fernet for users who want to protect credentials even from server compromise.
- **Rate limiting awareness** — Apple CalDAV and Google Calendar API both have rate limits. Handle with retry/backoff as needed; no proactive throttling strategy in v1.
- **Webhook/push notifications** — Google Calendar supports push notifications for changes. iCloud CalDAV does not. Could enable near-real-time one-way change detection from Google.
- **Shared calendar support** — iCloud shared calendars (family sharing) may have different CalDAV access patterns than personal calendars.
- **Frontend testing** — add Vitest when frontend complexity warrants it.
