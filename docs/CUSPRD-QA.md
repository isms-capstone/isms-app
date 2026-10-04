# CUS/PRD QA report

Updated on 2026-10-05 (Asia/Bangkok). Local branch: `feature/P1-CUSPRD`.
Changes are committed and pushed. No deployment or live database mutation
was performed. Requirement mapping and API contracts: [CUSPRD.md](CUSPRD.md).

## Delivery status

| Task | Implemented | Remaining dependency |
| --- | --- | --- |
| 01 | Organizations, contacts, multiple channel identities, search, UI | Staging verification |
| 02 | Products, per-product modules, customer instances, Admin UI | Staging verification |
| 03 | Contract dates, organization/department exam windows, UI | SLA calendar consumption |
| 04 | Not implemented | CAP case data and summary aggregation |
| 05 | Department and reusable course/exam registry, context selector | CAP form stores and validates selected IDs |
| 06 | Customer autocomplete, selection context, reusable picker | Actual CAP case form integration |
| 07 | Not implemented | ADM/CAT/SLA categories and SLA definitions |
| 08 | Default product team API/UI and routing context | ESC assignment logic |
| 09 | Instance context API and same-product SQL ranking hook | SIM/KB search endpoint integration |

## Executed checks

| Check | Result |
| --- | --- |
| `python -m pytest tests -q` from backend | 18 passed; 27 upstream deprecation warnings; latest 7.50 seconds |
| `npm run lint:registry` | Passed without errors |
| `PLAYWRIGHT_CHANNEL=msedge npm run test:registry-ui` | Passed using installed Edge |
| SQLite full Alembic upgrade/downgrade/reapply | Passed in backend tests |
| Migrated registry schema versus SQLAlchemy metadata | No differences across nine registry tables |
| `alembic upgrade head --sql` | MySQL SQL generation passed through `cusprd08` |
| Desktop/mobile layout | 1440px and 390px screenshots; mobile has no document horizontal overflow |
| Autocomplete input to visible choices | Local runs 211–223ms; latest 214ms |
| Actual MariaDB execution | MariaDB 11.4 isolated CI service: full upgrade/downgrade/re-upgrade and registry API workflow passed |
| GitHub CI | All four jobs passed at `f6e1494`: backend, browser, MariaDB and lint/configuration |

The timing is a local observation, not a staging load/network guarantee.
MariaDB checks now cover 11.4; the team deployment version remains unspecified.

## Coverage

Backend checks exercise Thai/name/channel search, literal wildcard escaping,
multiple channels, duplicate handling, product extensibility and scoped modules,
multiple instances, organization ownership, URL validation, reusable normalized
course text, partial contract updates, timezone-aware calendar intervals,
default teams and same-product ordering that retains other products.

Authentication checks use actual login/password hashing and JWTs, independent
role IDs, read/write permissions, expired tokens, refresh-token rejection at data
APIs, inactive-user rejection, and 20 concurrent authenticated reads.

Browser checks create organization/contact/channel/product/module/instance data,
departments/courses, contracts/exam windows and default teams. They verify context
selection, clearing IDs after input changes, Escape dismissing pending suggestions,
Auditor read-only controls, and delayed customer responses after navigation.
The final run reported no JavaScript errors.

## Defects found and fixed during this QA

- Invalid email channel values were accepted. They now return 422; regression
  test failed before the fix and passes afterward.
- Unknown customer input fields were silently ignored. They now return 422,
  including attempts to override organization ownership through a body field.
- Editing the selected customer cleared visible state without notifying the
  consumer. The context event now immediately supplies all five IDs as null.
- Pending autocomplete queries could reopen suggestions after Escape. Dismissal
  now cancels debounce/request and invalidates late results.
- The isolated QA server shared one SQLite connection across concurrent requests.
  It now uses a temporary file database with independent connections and WAL;
  concurrent-read and browser tests pass. Production database settings were unchanged.
- The browser readiness loop had lint violations; these were corrected and the
  dedicated registry lint command was added to CI.

## Before release

1. If deployment differs from MariaDB 11.4, repeat checks with that version/configuration and migrated customer data in staging.
2. Resolve INFRA deployment wiring: the current root Dockerfile starts a Node
   placeholder and Compose provisions PostgreSQL, while this backend uses MariaDB.
3. Confirm the final customer-editor role policy. Legacy INFRA `User` currently
   retains editor access alongside Admin, Agent and Team Lead.
4. Complete CAP/ADM/CAT/SLA/ESC/SIM integrations as listed above.
5. Integrate against INFRA/develop and run deployment smoke checks before release. Commits, push and GitHub CI verification are complete for this branch.

The implemented scope passes local QA and GitHub CI, including MariaDB 11.4. Tasks 01/02/03 can be marked implementation complete under this tested scope; tasks 05/06/08/09 have completed registry components with external integration pending. Full cross-module acceptance, production
load testing and production readiness remain unverified.

## Remote QA evidence (2026-10-05)

[All four jobs passed](https://github.com/isms-capstone/isms-app/actions/runs/37221513127) at `f6e1494`. Real MariaDB QA found task 08 rollback dropped its foreign-key backing index too early. Commit `f6e1494` drops the foreign key first; the complete migration round trip and API test then passed. Local tests report 18 passed and one MariaDB test skipped without the isolated service; CI executes that test successfully. Browser QA uses isolated SQLite separately.
