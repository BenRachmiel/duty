set dotenv-load

venv := justfile_directory() / ".venv/bin"

# list recipes
default:
    @just --list

# start backend + frontend dev servers
dev:
    #!/usr/bin/env bash
    trap 'kill $(jobs -p) 2>/dev/null' EXIT INT TERM
    just dev-back &
    just dev-front &
    wait

# start backend dev server
dev-back:
    cd backend && {{venv}}/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# start frontend dev server
dev-front:
    cd frontend && npm run dev

# run backend tests
test:
    cd backend && {{venv}}/python -m pytest tests/ -v

# build + start production stack (pulls from GHCR)
prod:
    docker compose up

# build + start production stack (detached)
prod-up:
    docker compose up -d

# stop production stack
prod-down:
    docker compose down

# build + start local container stack
dev-compose:
    docker compose -f compose.dev.yaml up --build

# build + start local container stack (detached)
dev-compose-up:
    docker compose -f compose.dev.yaml up --build -d

# stop local container stack
dev-compose-down:
    docker compose -f compose.dev.yaml down

# install all dependencies
install:
    {{venv}}/pip install -e "backend[dev]"
    cd frontend && npm install

# type-check frontend
typecheck:
    cd frontend && npx tsc -b --noEmit

# build frontend for production
build-front:
    cd frontend && npm run build

# seed database with test data (500 people, duties, rules) — requires running backend
seed:
    cd backend && {{venv}}/python seed.py
