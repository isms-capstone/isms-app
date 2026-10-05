# Incident & Service Management System (ISMS)

Project for Deverhood HT - Capstone Project.

## Customer / Product Registry

Implementation, local setup, task status and integration contracts:
[docs/CUSPRD.md](docs/CUSPRD.md).
The registry UI is served by FastAPI at `/registry`.

## Environments Setup
- Refer to .env.example for environment variables configuration.
- Do NOT commit .env files with sensitive secrets to this repository.

## Git Workflow Strategy
- main: Production environment
- develop: Integration and Staging
- feature/*: Isolated feature development

## Phase 1 integration / deployment

The integration branch combines INFRA, ADM, CUS/PRD and implemented CAP work.
See [merge review and deployment prerequisites](docs/PHASE1-MERGE-REVIEW.md).

The app now requires Alembic migrations before startup; seeding never creates tables.
For local Docker setup, copy `.env.example` to `.env`, replace its values, then run:

```sh
docker compose build app
docker compose up -d --wait db
docker compose run --rm app python -m app.db.migration_state
docker compose run --rm app python -m alembic upgrade head
docker compose up -d --wait app
```

Containers use `MARIADB_*` variables and the internal `db:3306` service. A backend
running outside Docker uses `backend/.env.example` with its actual published port.
Staging/production require separate untracked `.env.staging` / `.env.prod` files.
Changing these variables does not change credentials inside an existing MariaDB volume.
An existing database without Alembic history must be reviewed before migration;
the preflight intentionally stops and does not stamp or reset it.
