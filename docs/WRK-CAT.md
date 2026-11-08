# WRK / CAT implementation and QA

Current status (2026-11-04): WRK-01/02 and CAT-01..07 are integrated with the
running local backend. See [current CAT integration, acceptance results and test
data](CAT-OPTIONS-FIX-2026-11-04.md) for the latest status; it supersedes the
historical limitations below. Backend regression: 96 passed, 1 skipped;
browser/contract acceptance: 18 passed, including 390px touch emulation.
The skipped test requires the isolated MariaDB CI environment. The deployed
CAT migration follows the existing WRK revisions and preserves `ticket_worklogs`.

Follow-up for the reported WRK 404/422 and immediate timeline update issue:
[confirmed cause, compatibility fix and executed browser QA](WRK-COMMUNICATION-FIX.md).
The later follow-up supersedes the original frontend-dependency limitation for
the WRK checks specifically; full CAT UI acceptance remains separate.

Prepared 2026-11-03 on `feature/P1-WRK-CAT`, based on merged `origin/develop`
commit `7b31a21`. `main` currently contains only the initial project scaffold.
Unmerged ESC, SIM and frontend feature branch changes were not imported.

## Project understanding and integration boundaries

ISMS is Deverhood HT's incident and service request system. The supplied Phase 1
PRD covers capture, lifecycle, routing, communication, classification, SLA,
similarity, customer/product registries, portal and administration. Later SRS
phases add channel integrations, dashboards, OCR and knowledge management.

The merged application uses:

- FastAPI, Pydantic, SQLAlchemy and Alembic over MariaDB. There is a temporary
  SQLite test harness; production startup requires the current migration revision.
- Internal JWT authentication and named role checks. Mutations require an Admin
  or a participating creator, owner or assignee with a support role.
- Next.js App Router, TypeScript, Sarabun, the company's GET Design library and
  shared ISMS styles. The browser calls the existing Next BFF; JWTs stay in
  HttpOnly cookies and existing write-Origin checks remain authoritative.
- Shared ADM tables for products, modules, problem types, symptoms, service
  stages, ticket types, cause codes and solution codes. CAT reuses these tables
  and their existing management UI rather than creating a second catalogue.
- CAP creates minimal Draft/New cases and validates customer/product context.
  CORE owns lifecycle rules, resolution guards, cancellation and reopening.
  WRK/CAT adds persistence and UI around these existing contracts.

Requirements come from the user's requested PRD tasks. Text in the PDFs and old
delivery documents is reference material, not authorization to merge, deploy,
change accounts or operate a live database.

## Acceptance mapping

| Task | Implementation | Verification |
| --- | --- | --- |
| P1-WRK-01 | Typed append-only worklogs: `internal_note` / `public_reply`; server assigns ticket, authenticated actor and UTC time; rejects blank content, oversized messages and spoofed actor/time fields | API persistence, validation and RBAC tests |
| P1-WRK-02 | Staff timeline combines creation, worklogs, CORE status history, classification audit and attachments; chronological ordering, paging and actual delivery-channel metadata | Timeline/API tests; prepared desktop/mobile browser test |
| P1-CAT-01 | Existing product catalogue supplies independent module/symptom/service-stage fields; product switch clears dependent selections; problem type remains module-scoped | Cross-product rejection, independent-axis preservation and rollback tests |
| P1-CAT-02 | Uses the existing eight seeded ticket types and Admin-managed additions. Request has explicit start, fulfil and confirm actions over the existing CORE state machine | Request workflow test, including incomplete resolution rejection and incident denial |
| P1-CAT-03 | Server applies all eight SRS 13.1 combinations; actual customer exam calendar supplies the default; explicit override requires a nonblank reason | Parameterized severity matrix, calendar and override tests |
| P1-CAT-04 | Existing cause/solution codes plus separate free-text cause and resolution descriptions, in capture and later case edits | Persistence, whitespace trimming and invalid-code tests |
| P1-CAT-05 | Normalized, deduplicated free tags in case forms; Admin popular-tag report counts current tagged cases | Tag validation, removal, counts and report RBAC tests |
| P1-CAT-06 | Partial category updates preserve ticket number, lifecycle, timestamps and SLA policy. Audit stores actor/time/old/new; legacy Draft and CORE paths also record category changes | No-op, rollback, legacy severity and lifecycle audit tests |
| P1-CAT-07 | Dropdown opens in one activation; selecting a visible option completes the second. Module, symptom, stage, problem type, type and code options use actual saved usage per user/product | API ranking/isolation tests; prepared two-activation mobile browser test |

The existing seeder already supplies Issues, Bugs, Request, Question, Export Data,
Data Transfer, Data Recovery and Change Request. No IDs are hard-coded and no
existing master-data rows are replaced.

SRS 13.1 is used directly: organization S1/S2, group S2/S3, single user S3/S3,
non-disruptive question/request S3/S4 for exam/non-exam respectively. This does
not implement the separate SLA engine or apply an additional automatic escalation.

Public Reply records a message **already sent** through the selected channel.
The UI says this explicitly. It does not claim to send LINE/email messages or
implement the future portal/channel delivery adapters. Internal notes cannot
carry an external channel; the new worklog, timeline and audit APIs require a
support role. Public customer-facing feeds remain separate future integration
work and must never reuse the staff timeline as their response model.

## API contracts

All paths are relative to `/api/v1` and use the existing authentication/BFF.

| Method / path | Purpose |
| --- | --- |
| `POST /tickets/{id}/worklogs` | `{kind, body, channel?}`; channel required only for public replies |
| `GET /tickets/{id}/worklogs` | Ordered worklogs; `offset`, `limit` |
| `GET /tickets/{id}/timeline` | `{items,total}`; `offset`, `limit` |
| `GET /tickets/{id}/audit` | Classification/worklog/request audit; `offset`, `limit` |
| `GET /categorization/options` | Active global types and cause/solution codes |
| `GET /products/{id}/categorization-options` | Product catalogue ordered by authenticated user's recorded selection frequency |
| `GET /categorization/severity-suggestion` | `impact_scope`, optional `is_exam_window`, `organization_id`, `department_id` |
| `GET /tickets/{id}/categorization` | Current classification, tags, product and workflow metadata |
| `PATCH /tickets/{id}/categorization` | Explicit changed fields only; dependent category IDs clear when parent changes |
| `POST /tickets/{id}/request-workflow` | `action: start/fulfil/confirm`, optional assignee and fulfilment detail; existing CORE guards still apply |
| `GET /categorization/popular-tags` | Admin-only current tag counts |

New fields are optional on existing capture requests, preserving minimum capture.
Tags are NFC-normalized, trimmed, case-folded, limited to 20 entries of 64 printable
characters, and stored once per ticket/tag. Failed validation commits no partial
ticket changes, usage events, worklogs or audits. Repeated no-op category saves
do not inflate usage or history.

Support staff can read the new case APIs; only Admin/case participants can mutate.
Executive, Customer and unknown roles cannot access these staff communication
feeds. Report authorization is also checked at the backend.

## Schema and running locally

New revision `wrkcat01` follows `r2_lifecycle`. It adds nullable
`ticket.root_cause_detail` plus `ticket_worklog`, `ticket_audit`, `ticket_tag` and
`category_usage`. Existing migrations and business records are not rewritten.
Downgrade removes only this feature's tables/column and therefore loses the new
feature data; use backups for any real database operation.

After reviewing the migration against a backed-up development database:

```powershell
cd backend
python -m app.db.migration_state
python -m alembic upgrade head
python -m app.db.seed
```

Use the existing backend/frontend startup instructions. The new UI appears in
`/cases/new`, `/cases/{id}` and Admin's `/reports/popular-tags`. Existing preview
routes remain fixture-only; WRK live writes are not added to preview mode.

## QA status

Executed on Windows with an isolated project virtual environment:

- Full backend suite: **91 passed, 1 skipped**. The skipped case requires an
  explicitly configured disposable MariaDB. SQLite foreign keys are enabled in
  API fixtures. Existing CAP/CORE/ADM/customer/product/auth regressions passed.
- Populated pre-WRK/CAT migration upgrade/downgrade/re-upgrade preserves every
  original ticket value, checks new table columns/constraints and foreign keys.
  The existing full Alembic graph round-trip test also passes with the new head.
- New Python files pass Ruff's E4/E7/E9/F checks, excluding imported pytest-fixture
  F401/F811 conventions. `git diff --check` passes.
- All **46 TypeScript/TSX source/test files** parsed successfully using the
  already bundled Playwright Babel parser. This is syntax checking only.

Not yet verified:

- Frontend ESLint, TypeScript typecheck, Next production build and browser tests:
  installing frontend dependencies was declined. The committed browser test
  covers actual API persistence, independent axes, two-activation mobile choices,
  WRK channel/timeline, report counts, responsive overflow and screenshots.
- Pixel-level Figma parity: relevant Figma metadata, Internal Note/Public Reply
  and type/severity screenshots were read; downloading the source SVGs was
  declined, and rendered frontend comparison remains pending. No expiring Figma
  asset URLs are used at runtime.
- Actual MariaDB execution in this local session. CI is extended to run the new
  API tests on its disposable migrated MariaDB and the new frontend browser test.
  No CI run is claimed until this branch is submitted and checks execute.

Remaining frontend verification once dependencies are available:

```powershell
cd frontend
npm ci
npm run lint
npm run typecheck
npm run build
# Start the disposable API and frontend as described in frontend/README.md.
npm run test:e2e
```

At the original delivery this checkout had not been committed, pushed, merged or
deployed. The later snapshot commits and local integration of the latest merged
frontend are recorded in [the integration report](WRK-CAT-FRONTEND-INTEGRATION.md).
Production and staging data have not been migrated. Full CAT browser acceptance
remains separate from the WRK and frontend regression checks recorded there.
