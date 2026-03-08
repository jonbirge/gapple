# Gapple

Web service to do one thing: sync Google and Apple calendars to keep families from breaking apart...

Gapple is a self-hosted web application that provides bidirectional, manual sync between paired iCloud and Google calendars. It's built for Android users in families that share iCloud calendars.

## Prerequisites

- Python 3.12+
- Node.js 20+
- A [Google Cloud Console](https://console.cloud.google.com/) project with the Google Calendar API enabled and OAuth 2.0 credentials configured

## Local Development Setup

### 1. Clone and configure environment

```bash
git clone <repo-url> && cd gapple
cp .env.example .env
```

Edit `.env` and fill in:

- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from your Google Cloud Console OAuth 2.0 credentials
- `GAPPLE_ENCRYPTION_KEY` — generate one with:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

The API server runs at `http://localhost:8000`.

### 3. Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs at `http://localhost:5173` and proxies `/api` requests to the backend.

## Testing

### Backend tests

```bash
cd backend
pytest
```

All external API calls (Google Calendar, iCloud CalDAV) are mocked in tests — no real credentials needed.

### Linting and formatting

```bash
cd backend
ruff check .
ruff format .
```

## Database Migrations

After changing any SQLModel model in `backend/app/models/`:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
# Review the generated migration in alembic/versions/ before applying
alembic upgrade head
```

## Production Deployment

Gapple is deployed as a single Docker container via Docker Compose on a Linux VPS.

### 1. Prepare the server

Ensure Docker and Docker Compose are installed on your VPS. Set up a reverse proxy (nginx, Caddy, or Traefik) to terminate TLS and forward traffic to port 8000.

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with production values:

- Set `GOOGLE_REDIRECT_URI` to your production callback URL (e.g., `https://gapple.example.com/auth/google/callback`)
- Set `GAPPLE_BASE_URL` to your production URL (e.g., `https://gapple.example.com`)
- Generate a fresh `GAPPLE_ENCRYPTION_KEY` for production — do not reuse your dev key

### 3. Build and run

```bash
docker compose up -d --build
```

This builds a multi-stage Docker image (Node frontend build, then Python runtime) and starts the service. The SQLite database is persisted in the `./data/` volume mount.

### 4. Apply migrations

```bash
docker compose exec gapple alembic upgrade head
```

### 5. Verify

```bash
docker compose logs -f gapple
```

The app should be accessible through your reverse proxy at your configured domain.

### Updating

```bash
git pull
docker compose up -d --build
docker compose exec gapple alembic upgrade head
```

### Reverse proxy example (Caddy)

```
gapple.example.com {
    reverse_proxy localhost:8000
}
```

Caddy automatically provisions and renews TLS certificates via Let's Encrypt.
