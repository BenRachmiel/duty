# Duty

Tag-based duty roster system with a constraint solver for fair assignment.

Define people and duties, tag them, create rules mapping tags to eligibility, and let an OR-Tools CP-SAT solver fill rosters fairly by weighted points. The solver maximizes coverage first, then minimizes the highest individual workload so no one gets buried.

## How it works

**People** and **duties** each carry **tags** (e.g. _medic_, _officer_, _night-shift_). **Rules** connect them:

| Rule type | Effect |
|-----------|--------|
| **Allow** | Only people with the matching tag are eligible (whitelist) |
| **Deny** | People with the matching tag are excluded |
| **Cooldown** | After a tagged duty, the person can't do another tagged duty for N days |

Without any allow rules for a duty tag, everyone is eligible by default.

**Points** = `duration_days * difficulty` per assignment. The solver balances total points across personnel so duties are distributed fairly. A two-phase solve ensures maximum coverage before optimizing fairness.

## Running it

```
docker compose up -d
```

Open [localhost:8080](http://localhost:8080).

Data persists in a Docker volume (`db-data`). To start fresh: `docker compose down -v`.

### Local dev (requires Nix + direnv)

```
just dev
```

Starts the FastAPI backend and Vite dev server with hot reload.

### Smoke test

```
just push-check
```

Builds images locally, brings up the full stack via `compose.dev.yaml`, verifies backend and frontend respond through nginx, then tears down. Also runs in CI on every PR (`.github/workflows/compose-smoke.yml`).

### Health endpoint

`GET /healthz` — returns `{"status": "ok"}`. Used by Docker Compose healthchecks to gate container readiness.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python, FastAPI, SQLAlchemy (async), SQLite, OR-Tools |
| Frontend | React, shadcn/ui, Tailwind, TanStack Query |
| Infra | Docker Compose, nginx reverse proxy |
