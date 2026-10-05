# CUS/PRD QA report

Updated 2026-10-05 (Asia/Bangkok). Branch feature/P1-CUSPRD is committed and pushed.
No customer database or external deployment was modified.

## Current delivery

| Task | Implemented | Remaining scope |
| --- | --- | --- |
| 01 | Customer/contact/channel API and UI | Deployment smoke check when deployed |
| 02 | ADM-backed shared product/module catalogue and customer instances | Deployment smoke check when deployed |
| 03 | Contract dates and organization/department exam calendar | SLA engine consumes calendar later |
| 04 | Not implemented | CAP case data and summary aggregation |
| 05 | Department/course registry and context selector | CAP form integration |
| 06 | Autocomplete/context API and UI | CAP form integration and target-environment timing |
| 07 | ADM-backed category/SLA configuration UI/API and ownership validation | Actual CAP case-form acceptance |
| 08 | ADM team assignment and routing context | Future ADM-06/ESC rules consume it if present |
| 09 | Instance parameter/search context, SQL ranking hook and SIM usage documentation | Future SIM/KB integration |

01/02/03 meet their task implementation acceptance criteria. Task 09's requested
hook/documentation exists; do not confuse that delivery with the future SIM engine.
Do not mark the full task 07 case-form acceptance complete while CAP is absent.

## Executed checks

- Local backend: 22 passed, one MariaDB-only test skipped without its disposable
  database. Current deprecation warnings originate from existing config/assets
  schemas and datetime defaults.
- Registry JavaScript lint passed.
- Browser on installed Edge passed actual login, customer/product/module/instance
  creation, team assignment, department/course/contract/calendar, autocomplete,
  desktop/mobile and read-only controls. The expanded workflow also creates
  symptoms/stages/problem types and a product SLA/rule through UI.
- Latest local autocomplete observation: 204ms, not a production-load guarantee.
- Cross-product category IDs rejected; inactive categories/modules/policies
  excluded; unknown policy 404; inactive assignment 409; non-Admin writes 403.
- Actual JWT checks include expired/refresh tokens, inactive accounts and concurrent reads.
- ADM-created products/modules are visible through registry endpoints; registry
  writes are visible through ADM; edits/deactivation reflect immediately.
- Schema comparison passes for the nine current registry tables.
- Migration tests include populated legacy/ADM catalogues with different IDs,
  preserved default teams/codes/modules and remapped customer instances.

[All four CI jobs passed for task 07 at a4166fc](https://github.com/isms-capstone/isms-app/actions/runs/37263852342):
backend, browser, lint/configuration and MariaDB 11.4. MariaDB executes populated
catalogue consolidation, verifies data references, downgrades to base, re-upgrades
and runs registry plus category/SLA API checks. The earlier integration-only run
also passed at bf737f8. Latest validation fixes are tracked in subsequent commits.

## Defects corrected

- Invalid email and unknown customer fields now return 422.
- Search edits clear all selected IDs and dispatch context events; Escape cancels
  pending autocomplete work; delayed responses cannot overwrite a new view.
- QA SQLite preview uses separate connections rather than a shared transaction.
- MariaDB rollback drops the default-team FK before its supporting index.
- Duplicate Product/Module models were replaced by canonical ADM aliases;
  instance references are migrated rather than assuming IDs coincide.
- Product/module/stage/problem-type lengths agree with ADM database columns;
  blank names and null updates to mandatory SLA rule fields are rejected.
- Form selects now use their first option when no value/default is supplied.
  Browser QA caught the previous invalid empty selection blocking problem creation.

## Remaining deployment/integration limits

Dockerfile/Compose now come from ADM and target FastAPI/MariaDB; the old
Node/PostgreSQL mismatch is gone. Full Docker startup was not run locally because
Docker Desktop is unavailable. CI exercises MariaDB 11.4; check any differing
team database version/collation and migrated customer data before deployment.
ADM-05/06 and CAP/ESC/SIM/SLA execution are outside this implementation.

See [CUSPRD-ADM.md](CUSPRD-ADM.md) for migration safeguards and consuming API contracts,
and [CUSPRD.md](CUSPRD.md) for the full registry API guide.
