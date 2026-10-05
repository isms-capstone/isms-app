# Phase 1 integration review — 5 October 2026

Target: develop. Preparation branch: integration/P1-round1.
The user authorized preparing this branch, integration fixes, QA and a review PR.
The user subsequently authorized merging into develop without deployment.
Staging deployment is manual-only and restricted to develop.

## Included histories

| Remote branch | Audited head | Handling |
| --- | --- | --- |
| feature/P1-CAP | 27b5a73 | Integration base; implemented CAP and all CUS work |
| feature/P1-CUSPRD | 07fe675 | Already ancestor of CAP |
| feature/P1-ADM | 74ef224 | Already ancestor of CAP, with compatibility/rollback fixes on CAP |
| feature/P1-INFRA | 0b2ea25 | Already ancestor of CAP |
| feature/p1-gitops-infra-setup | 2104e4b | Already ancestor of CAP |
| feature/P1-GITOPS-01-setup | 1febed5 | Merged into preparation branch, preserving history |
| P1-GITOPS-06 | 3a69bf5 | Merged into preparation branch, preserving history |
| main | 8929f69 | Only divergent change is a branch-protection test comment; excluded |
| develop | d649382 | Unchanged target, initial repository structure |

Gitops merges had no conflicts. No squash is proposed: preserving ancestry avoids
repeating the already integrated INFRA/ADM/CUS branches. PR #1/#2 remain open;
their work is included here, but they should only be closed after the final merge.

## Integration fixes

- Root Docker env template now uses the backend's MARIADB_* names.
- Compose passes DB/JWT values to the app and uses MariaDB internal port 3306.
  Published DB ports are loopback-only; staging/prod require configured credentials.
- Explicit environment overlays avoid the development bind-mount override on servers.
- Deploy builds the image, starts/waits for DB, checks migration history read-only,
  runs `python -m alembic upgrade head`, then replaces/waits for the app.
- Missing env file, wrong commit, unmanaged existing database or failed migration
  stops deployment. No auto-stamp, schema reset, volume deletion or ignored migration error.
- Startup/seeding checks current Alembic head instead of using create_all.
- CI validates all Compose overlays, deployment order/failure guards, idempotent seed,
  actual Docker image startup on migrated MariaDB, and the existing backend/browser QA.
- Staging/production workflows serialize deployments. Production's obsolete npm migration
  command was replaced with the same Alembic pipeline; no production deployment is triggered.

## Required before deployment (deferred by user)

1. Read-only staging inspection: confirm host/user, checkout, Compose project/DB volume,
   database version history and existing schema. This is pending confirmed SSH access.
   Never run a real upgrade/downgrade, change accounts, stamp history or restart staging
   during this read-only inspection.
   After the host is confirmed, `bash scripts/inspect-staging.sh` reports only checkout,
   container/volume metadata, table names and Alembic revisions. Its database commands
   are SELECT/SHOW only; it does not print environment values or customer records.
2. The user accepts self-review instead of the original teammate-review requirement.
   Confirm a backup before migrating a database containing valuable data.
   Existing tables created without Alembic need a reconciliation
   plan; the CI's fresh/migrated DB does not prove the live DB state.
3. Configure repository ONPREM_HOST, ONPREM_USER, ONPREM_SSH_KEY (and optional
   ONPREM_SSH_PORT) plus server env files. Read-only API audit found no repository
   Actions secrets and no GitHub environments at preparation time. Secret values
   cannot be retrieved from GitHub. No secrets/protection settings were changed.
4. Confirm the intended production environment approval rule; the workflow names
   `production`, but that GitHub environment is currently absent.
5. GitHub-required PR review may still need a teammate's approval. The user has
   explicitly approved merging without deployment. Existing PRs #1/#2
   show REVIEW_REQUIRED. The develop protection API did not expose a complete policy;
   no bypass or protection change is proposed.

## Scope / acceptance still tracked

This PR is integration of implemented work, not a claim that all Phase 1 tasks are Done.
CAP-06 inline editing is complete; CAP-04 needs real-user 30-second evidence;
CAP-08's capture/time-edit side is ready but actual SLA calculation is downstream.
CAP-03/05/07/10/11 and ADM's case-template/rule execution integrations remain with
their assigned owners. See CAP-REMAINING-QA.md and ADM-CUS-CAP-INTEGRATION.md.

## Validation

Local backend: 47 passed, 1 skipped (isolated MariaDB-only test).
Deploy order/failure unit tests: 3 passed using shell stubs, without contacting a server.
Compose local/staging/prod validation and git diff --check passed.
Code commit d4d4e4f passed all four CI jobs, including actual image startup:
[CI run 37307301534](https://github.com/isms-capstone/isms-app/actions/runs/37307301534).
Review: [Draft PR #3](https://github.com/isms-capstone/isms-app/pull/3).
Staging remains uninspected because its confirmed SSH host/user has not been supplied.
