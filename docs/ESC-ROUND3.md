# Round 3 — Escalation & Routing (P1-ESC-01..09)

Base: `develop` merge `7b31a21` (Round 2 PR #6, merged 30 October 2026). Work branch: `feature/P1-ESC`.
Scope follows `ISMS_Phase1_PRD.pdf`, pages 14–16. This change does not implement WRK, SLA calculation, KPI dashboards or deploy anything.

## Delivered behavior

| Task | Backend / persistence | Frontend |
| --- | --- | --- |
| ESC-01 | Product + Tier 2/1/0 routes using canonical ADM products/teams; user default tier | Admin → Escalation & Routing (`/routing/admin`) |
| ESC-02 | Versioned handoff requires nonblank reason, checked and requested; immutable routing event linked to status history | Three required fields and case routing timeline |
| ESC-03 | Handoff changes Assignee, preserves Owner and customer communication responsibility | Owner / Assignee displayed separately |
| ESC-04 | Tier entry/exit intervals, history references and per-tier accumulated seconds | Tier 2/1/0 elapsed-time summary |
| ESC-05 | Return latest outstanding handoff with required advice/reason; same ticket ID/number/created time | Destination assignee/team lead sees return form |
| ESC-06 | Configurable S1 response timeout, durable head notification and automatic one-tier escalation | Admin timeout + notification bell + response acknowledgement |
| ESC-07 | Self-assign unassigned NEW case; responsible head/Admin manual assignment | Case action buttons and eligible recipient selection |
| ESC-08 | Five-minute worker, NEW older than 15 minutes, business calendar/holiday checks | Head notification links to case |
| ESC-09 | Availability switch; atomic transfer of the complete active assigned workload with reason | Work → การส่งมอบงาน (`/routing`) |

## Contracts and integration

- Explicit product/tier route takes precedence. Tier 2 then uses existing ADM Automation Rules, product default team, and finally the existing participant's team. There is no second product/team catalogue.
- A recipient must be active, available, in the destination team and have the matching default tier. Missing destinations produce an actionable validation error; automatic escalation alerts the head/Admin instead of silently dropping a case. Heads fall back to the existing Team Lead role in that team, then active Admins if no head is configured.
- Support roles: Admin, Agent, Specialist, Developer and Team Lead. Case participants or the responsible lead may escalate; only the destination assignee/head may return; only the responsible head/Admin may manually assign. Read-only roles see history with no mutation actions.
- Handoff may move Tier 2 → 1/0 or 1 → 0. Automatic escalation advances one tier at a time. Tier 0 has no higher destination and continues to alert its head.
- `expected_version` plus row locks/conditional updates rejects stale requests. Bulk transfer locks the workload, validates all recipients first and commits all cases together. A changed workload must be refreshed; it is never partially transferred.
- Owner, ticket number, creation time and case status remain unchanged by routing/return. Returning does not create another case for future KPI-01. Existing CORE lifecycle changes close/reopen tier intervals and invalidate stale routing versions.
- Times are UTC in storage. Per-tier totals are elapsed wall-clock time including pending periods, **not business-hours SLA**. Initial legacy intervals are marked estimated because prior tier transitions were not recorded. New intervals reference `ticket_status_history`.
- First response is the existing `first_response_at`, recorded when work enters IN_PROGRESS or the operator explicitly acknowledges the case. This is an operational acknowledgement, not a new public customer reply/WRK feature.
- S1 no-response checks run all hours, with a fresh timeout after handoff/return. Publishing an old draft starts its NEW/S1 timer at publication rather than draft creation. NEW alerts follow the selected ADM business calendar, timezone, weekdays and holidays; fallback is Monday–Friday 08:00–17:00 Asia/Bangkok.
- Notifications are durable **in-app** records. No email, Slack or LINE message is sent. The bell polls every 60 seconds and only exposes its authenticated recipient's notifications.
- A database lease prevents overlapping worker runs and repeated execution inside five minutes. Timestamp tokens use second precision to match MariaDB DATETIME. Worker failure rolls back routing and permits retry; a crashed worker's lease expires after nine minutes.
- Company `@DeverhoodHT/get-design` Button/Input/Checkbox primitives are reused. Layout, fonts and six CI colors stay consistent with the current Next.js interface. Desktop and mobile layouts are covered by browser acceptance tests.
- Next.js BFF now permits PUT with the same session and Origin protection as POST/PATCH; this is required for routing configuration and availability.

## Migration and local startup

Revision `esc01_routing` follows `r2_lifecycle`. It adds user defaults/availability, a routing version and seven routing tables. Existing cases/users remain; active cases get estimated initial intervals. There is no reset, stamp, drop of existing tables or automatic seeding.

For an existing environment, first keep a normal database backup. Use the **same Compose project name, env file and local overlay already used by that environment**, so it keeps the existing database volume. Follow the established README migration preflight/build process, then:

```sh
# Run from repository root; example uses the checked-in local overlay.
docker compose -f docker-compose.yml -f docker-compose.local.yml build app
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --wait db
docker compose -f docker-compose.yml -f docker-compose.local.yml run --rm app python -m app.db.migration_state
docker compose -f docker-compose.yml -f docker-compose.local.yml run --rm app python -m alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.local.yml -f docker-compose.frontend.yml -f docker-compose.routing.yml up -d --build app frontend routing-worker
```

Without Docker, run `python -m app.jobs.routing_worker` from `backend` in a separate terminal with the same database environment as the API. The worker refuses to start against a stale schema. Admin should configure product/tier teams, user tiers and heads before expecting automatic assignment. `/routing/admin` reports the worker's last successful check. `/preview` remains a read-only visual fixture; use authenticated pages to operate routing.

## Verification

Local validation: backend regression tests (including the new ESC suite), frontend lint/typecheck/production build, and six real browser flows. Screenshots are saved under ignored `frontend/test-results/`. CI provides the additional migrated MariaDB and concurrent row-lock check.

- `backend/tests/test_routing.py`: required handoff context, owner preservation, same-case return, interval/history linkage, eligibility and RBAC, stale versions, all-or-nothing bulk handover, settings, availability, job timeout/idempotency, business hours/holidays, missing destinations, response acknowledgement and timestamp precision. A real concurrent self-assignment test runs on migrated MariaDB in CI.
- Existing backend regression and migration upgrade/downgrade suite is retained.
- `frontend/tests/routing.spec.ts`: real cookie-authenticated Next.js → API handoff/return, self-assign, availability, bulk transfer, Admin policy, bell, desktop/mobile and read-only denial. Cross-origin PUT is rejected.
- Existing four frontend browser flows remain intact; lint, TypeScript and production build are required.
- CI MariaDB job runs migrations and ESC tests against disposable MariaDB. Compose worker overlay validation is included.

No local existing project database has been migrated during implementation. Local Docker engine startup is currently unavailable; migration/row-lock validation is also configured on the CI MariaDB service. Remote checks and their exact outcome should be reviewed on the ESC PR before merging.
