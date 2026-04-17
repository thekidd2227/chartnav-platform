# ChartNav Platform

Monorepo for the ChartNav platform — an ophthalmology-first clinical workflow system.

- `apps/api` — FastAPI backend
- `apps/web` — Vite + React frontend (ChartNav Platform)
- `infra/docker` — Docker Compose starter

## Quick start

### API (local)

```
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

Health check: `curl http://localhost:8000/health`

### Web (local)

```
cd apps/web
npm install
npm run dev
```

Opens on http://localhost:5173

### Docker Compose (api + web)

```
cd infra/docker
cp ../.env.example ../.env
docker compose up --build
```

- API: http://localhost:8000
- Web: http://localhost:5173

## Env files

Copy the examples before running:

```
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
cp infra/.env.example infra/.env
```
