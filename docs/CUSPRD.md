# Customer / Product Registry implementation

Source: ISMS Phase 1 PRD (tasks 01–09) and DVHT-ISMS-SRS-002 v1.3, section 8.9.

Latest QA findings and release limits: [CUSPRD-QA.md](CUSPRD-QA.md).

## Git workflow

Local branch: `feature/P1-CUSPRD`, based on `origin/feature/P1-INFRA`
at `0b2ea25`. At inspection time `develop` contains only the initial repository
commit, so it cannot yet serve as the implementation base. This is a stacked
feature: merge/review INFRA into develop first, then update this branch and
open its PR against develop. Do not merge unrelated ADM work into this branch.
No remote branch has been pushed and no PR has been created.

Suggested commit: `feat(cus): add customer registry [P1-CUSPRD-01]`.
Task 02 commit: `feat(prd): add product registry [P1-CUSPRD-02]`.
After INFRA integration, fetch and merge `origin/develop` into this feature,
run tests, inspect the diff against develop, then push with
`git push -u origin feature/P1-CUSPRD` and create a reviewed PR to develop.

## Delivery and dependencies

| Task | Scope | Readiness |
| --- | --- | --- |
| P1-CUSPRD-01 | Organizations, contacts, channel identities, search API | Implemented in this change; no ADM dependency |
| P1-CUSPRD-02 | Products, instances, product modules | API + Admin UI implemented |
| P1-CUSPRD-03 | Contract dates, exam windows | API + customer UI implemented; SLA engine consumes the calendar later |
| P1-CUSPRD-04 | Open cases and frequent problems summary | Requires CAP ticket data and agreed aggregation |
| P1-CUSPRD-05 | Departments and reusable course/exam registry | API + management UI + selectable context implemented; CAP connects IDs later |
| P1-CUSPRD-06 | Case customer autocomplete and auto-fill | API + reusable picker + context selection UI implemented; final CAP form integration remains |
| P1-CUSPRD-07 | Per-product categories and SLA | Coordinate with ADM/CAT/SLA |
| P1-CUSPRD-08 | Default responsible product team | API + Admin UI implemented using INFRA teams; ESC consumes routing context later |
| P1-CUSPRD-09 | Same-product search ranking hook | Query parameter + context API + SQL ordering hook implemented; SIM/KB consumes it later |

Delivered in order: 01 -> 02 -> 05 -> 03 -> 06 -> 08 -> 09.
All registry work independent of ADM is implemented. Tasks 04 and 07 are not
implemented: 04 depends on CAP ticket data; 07 depends on ADM/CAT/SLA registries.
Task 06's actual case creation form remains CAP integration work, not a fake
ticket form in this module. Existing repository branches had no frontend project;
the registry now includes a same-origin vanilla HTML/CSS/JS UI served by FastAPI.
Its sidebar, colours and tables follow the supplied visual reference. It exposes
registry workflows only, rather than pretending other case modules already exist.

## Run the application locally

Use the team's MariaDB instance and existing INFRA environment configuration.
`backend/.env.example` lists the names this backend actually reads; copy it to
`backend/.env` and replace placeholders, or supply them through environment vars.
From the repository root in PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
Set-Location backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Configure `MARIADB_SERVER`, `MARIADB_PORT`, `MARIADB_USER`, `MARIADB_PASSWORD`,
`MARIADB_DB` and `SECRET_KEY` in the existing backend environment before running.
Open `http://127.0.0.1:8000/registry`; API documentation is at `/docs`.
Login uses the existing `/api/v1/auth/login`, access JWT and active-user check.
Tokens are kept in memory only; refresh/reload requires login again. The public
HTML shell contains no customer data; each data API is authenticated separately.
Writes remain protected by API RBAC even when a client bypasses the UI controls.

The root Dockerfile/Compose in the checked-out INFRA branch still starts a Node
placeholder and a PostgreSQL service, while this FastAPI backend targets MariaDB.
Those existing deployment files are not a verified backend deployment path.
Use the backend commands above or the team's working backend environment; agree
deployment wiring with the INFRA owner before staging/production deployment.
No live database migrations, external deployments, push or PR have been run here.

## Isolated QA preview and browser checks

The preview runs only on `127.0.0.1:8765`, with an ephemeral SQLite database and
explicit test accounts, never the team's customer database:

```powershell
# Terminal 1, from repository root
.venv/Scripts/python.exe backend/tests/preview_registry.py

# Terminal 2
npm ci
npx playwright install chromium
npm run test:registry-ui
```

QA accounts: `qa-admin`, `qa-agent`, `qa-auditor`; password `test-only-password`.
These accounts exist only in the test preview. Restart the preview before each
browser run to reset fixtures. Browser checks create data only in that preview.
Screenshots are written to ignored `backend/tests/ui-output/`.
For an installed Edge browser, set `PLAYWRIGHT_CHANNEL=msedge` before the test.
CI now runs both backend tests and the isolated browser workflow, retaining
screenshots and server logs as an artifact. CI has not yet run on GitHub.

## P1-CUSPRD-01 API

All paths below are relative to `/api/v1/customers`. Authentication uses the
existing access JWT. Authenticated active users can read. Admin, Agent and
Team Lead can write; legacy INFRA User can write until ADM role migration.
This interim permission mapping must be reviewed with the team before release.
Auditor and other roles cannot write. Role names avoid hard-coded database IDs.

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | /organizations | List/search or create |
| GET/PUT | /organizations/{id} | Read or replace name/active state |
| GET | /contacts | Search; optional organization_id filter |
| POST | /organizations/{id}/contacts | Create an organization's contact |
| GET/PUT | /contacts/{id} | Read or replace name/active state |
| POST | /contacts/{id}/channels | Add contact channel |
| DELETE | /contacts/{id}/channels/{channel_id} | Remove that contact's channel |

Organization/contact input: `{"name":"มหาวิทยาลัย TU","is_active":true}`.
Channel input: `{"channel_type":"email","value":"teacher@tu.ac.th"}`.
Types: `line_user_id`, `line_group_id`, `email`, `phone`.
Email values are validated, trimmed and normalized. Unknown input fields are rejected.
Other identifiers are trimmed and
stored as supplied; telephone international normalization is not assumed.
Same channel type/value on the same contact returns 409. Shared group IDs
across contacts are allowed. Organization names need not be globally unique.
Organization/contact removal uses `is_active=false` to preserve references.
List responses include inactive records for registry management.

Search accepts `q`, `offset` (default 0), `limit` (default 25, maximum 100).
Organization search matches organization name, its contact names or channels;
contact search matches contact name or channels. `%` and `_` are literal input.
Ordering is name then ID. This is substring search, not fuzzy search. Contact
responses include their channels. Missing parent records return 404; empty
names, invalid channel types and excessive lengths return 422.

## P1-CUSPRD-02 API

These paths are relative to `/api/v1` (not `/api/v1/customers`).
Active authenticated users can read. Only Admin can change products/modules;
the customer registry editor roles can create/update instances. Products/modules
are catalogue data, while instances belong to individual customers.

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | /products | List/search or create products |
| GET/PUT | /products/{id} | Read or replace product fields |
| GET/POST | /products/{id}/modules | List or add this product's modules |
| PUT | /products/{id}/modules/{module_id} | Update this product's module |
| GET | /product-instances | Search/filter customer installations |
| POST | /organizations/{id}/products/{product_id}/instances | Add customer installation |
| GET/PUT | /product-instances/{id} | Read or update installation details |

Product/module input: `{"code":"examplus","name":"ExamPlus","is_active":true}`.
Module examples for ExamPlus: `teacher`, `proctor`, `student-web`, `student-app`.
GetA, Logbook and future services are ordinary product rows; there is no product
enum, fixed product list or schema migration when adding another product.
Product catalogue data is created through the Admin-only API; no demo records
are inserted into an existing customer database automatically.

Instance input:

```json
{
  "code": "production",
  "name": "TU ExamPlus",
  "version": "1.2.3",
  "environment": "production",
  "url": "https://exam.example.org",
  "is_active": true
}
```

Codes are trimmed, lowercased and restricted to ASCII letters, digits, `_` and
`-`, beginning with a letter/digit. Product codes are unique globally; module
codes within a product; instance codes within an organization/product pair.
One organization may have multiple installations/environments of a product.
Duplicate codes return 409, unknown parents 404, invalid fields 422. Product and
organization references cannot be reassigned through the instance update body.

URLs require HTTP/HTTPS, allow at most 2048 characters and reject embedded
credentials. URLs are stored as metadata and are never fetched by the API.
Versions and environment labels are required text fields; environment labels
are trimmed/lowercased and allow future environments without schema changes.
Products, modules and instances can be deactivated using `is_active=false`;
there is no hard-delete endpoint that could break future ticket references.
Deactivation does not cascade to existing child rows. Lists include inactive
rows unless filtered with `is_active`; instance active state is independent of
the parent product/organization active state.

Lists use `offset`/`limit` as task 01. Products support `q` (name/code) and
`is_active`; modules support `is_active`; instances support `q` (name/code),
`organization_id`, `product_id`, `is_active`. Product responses include all their
modules, including inactive ones. Filter the module endpoint for active choices.
The Product Registry page lets Admin add/edit products and modules. Customer
detail pages manage product instances. The API is also available through `/docs`.

## P1-CUSPRD-05 reusable department/course registry

Paths below are relative to `/api/v1/customers/organizations/{organization_id}`:

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | /departments | List/search or add a department |
| PUT | /departments/{id} | Edit/deactivate a department |
| GET/POST | /courses | List/search or add/reuse course or exam text |
| PUT | /courses/{id} | Edit/deactivate a course/exam |

Department input is `{"name":"Medicine Faculty","is_active":true}`.
Course input adds `"kind":"course"` or `"kind":"exam"` (default `course`).
Names are NFC normalized, trimmed, whitespace-collapsed and indexed for
case-insensitive reuse within each organization. Department duplicates return
409. POSTing the same organization/kind/normalized course text returns its
existing ID with 200 (new rows return 201), including concurrent requests.
An existing entry with a different active state returns 409; explicitly PUT to
change that state. Different organizations have independent registries.
Updates cannot move a row across organizations. Cross-organization IDs return 404.
Lists accept `q`, `is_active`, `offset`, `limit`; courses also accept `kind`.
The context selector shows only active choices and stores their IDs. CAP should
reuse these IDs and validate organization ownership, not store free text again.

## P1-CUSPRD-03 contract and calendar

Under the same organization path:

| Method | Path | Purpose |
| --- | --- | --- |
| GET/PATCH | /contract | Read/update nullable start/end dates |
| GET/POST | /exam-windows | List/add exam windows |
| PUT | /exam-windows/{id} | Update/deactivate a window |

Contract input accepts `contract_start_date` and `contract_end_date` in ISO date
format; absent fields remain unchanged, explicit null clears a date. If both are
present, end must be on/after start, including partial updates against stored dates.
Customer detail UI supports setting/clearing these dates.

Exam input: `{"name":"Final exam","department_id":null,
"starts_at":"2026-10-05T09:00:00+07:00","ends_at":"2026-10-05T12:00:00+07:00",
"is_active":true}`. A null department applies to the whole organization; a
department ID must belong to that organization. Composite database FK constraints
enforce the same rule even outside the API. Overlapping windows are permitted.
Input datetimes require an explicit timezone offset, API output is UTC, and
MariaDB stores UTC DATETIME. The UI displays/edits the device's local time and
converts it before submission. No end-before-start or zero-length windows.

SLA can GET `/exam-windows?active_at=<offset-aware datetime>&department_id=<id>`.
The active interval is `[starts_at, ends_at)`: inclusive start, exclusive end.
This excludes inactive windows and includes organization-wide windows as well
as the chosen department's windows. Without `active_at`, lists include inactive
windows unless `is_active` filters them. SLA severity changes belong to SLA.

## P1-CUSPRD-06 autocomplete integration

`GET /api/v1/customers/autocomplete?q=<text>&limit=10` returns at most 20 choices:
`{"organization": {...}, "contact": {...}|null}`. Search matches organization
names, active contact names or contact channels, excluding inactive organizations
and contacts. Choices distinguish organization-only and individual-contact matches.

On selection, GET `/api/v1/customers/organizations/{id}/selection-context` with
optional `contact_id`. It validates ownership and returns organization/contact,
active instances of active products, active departments and reusable courses.
The UI auto-selects the instance when exactly one is available; multiple instances
remain explicit user choices. Changing search text clears the previous context
immediately, aborts old queries and ignores stale selection responses.

The picker at `/registry/assets/autocomplete.js` exports
`mountCustomerAutocomplete(input, list, authenticatedRequest, onSelect, onError,
onInput)`, returning a cleanup function. It uses 120ms debounce, AbortController
and keyboard navigation. CAP can reuse that picker and the selection API. The
current context UI dispatches `customer-context-change` with `organization_id`,
`contact_id`, `product_instance_id`, `department_id`, `course_or_exam_id` when
the selection changes. Editing the search dispatches all five IDs as null immediately.
It does not POST tickets; wire these IDs into CAP's form.
Local browser QA measured 211–223ms (latest 214ms) from input to visible choices; this is not a
500ms guarantee for staging load/network or the final CAP integration.

## P1-CUSPRD-08 default product team

Admin PUT `/api/v1/products/{id}/default-team` with
`{"default_team_id":<existing team ID>|null}` to set/clear the default team.
An unknown team returns 404. The Product Registry detail UI selects from the
existing INFRA team table through authenticated `/api/v1/registry/teams`.
No duplicate team CRUD or alternative ADM team registry is introduced.
ESC reads `/api/v1/products/{id}/routing-context`, returning `product_id` and
`default_team_id`; null means unconfigured, not an arbitrary fallback team.
Automatic assignment rules and owner/assignee decisions remain ESC work.

## P1-CUSPRD-09 SIM/KB hook

`GET /api/v1/registry/search-context?product_instance_id=<id>` resolves the
preferred product while retaining `include_other_products=true`. Without an
instance the preference is null; unknown instances return 404. Same-product
preference includes other customer installations of that product.

For SIM/KB backend queries, use `app.services.product_search`:

```python
context = resolve_search_context(db, product_instance_id)
query = query.order_by(
    product_preference_order(candidate_product_id_column, context),
    relevance_score.desc(),
    candidate_id_column,
)
```

`candidate_product_id_column` must be the candidate's product ID, joined through
its instance if necessary. The CASE expression prioritizes the same product and
does not add a WHERE filter. Keep existing relevance scoring, permissions and
stable ID ordering; apply preference before pagination. This module does not
invent ticket/KB tables or a similarity engine. SIM's eventual search endpoint
must accept the documented `product_instance_id` parameter and consume this hook.

## Files and verification

- `backend/app/db/models/customer.py`: ORM tables and constraints.
- `backend/app/schemas/customer.py`: validated input/output schemas.
- `backend/app/api/v1/endpoints/customers.py`: authenticated API and search.
- `backend/app/api/v1/router.py`: mounts registry routes.
- `backend/alembic/env.py`: registers customer metadata.
- `backend/alembic/versions/cusprd01_customer_registry.py`: explicit reversible migration.
- `backend/tests/test_customers.py`: acceptance, permission and migration tests.
- `backend/requirements-dev.txt`: test dependencies.
- `.github/workflows/ci.yml`: adds a backend test job alongside existing checks.
- `backend/app/db/models/product.py`: product, module and instance ORM tables.
- `backend/app/schemas/product.py`: catalogue and installation validation.
- `backend/app/api/v1/endpoints/products.py`: registry API and role permissions.
- `backend/alembic/versions/cusprd02_product_registry.py`: follows cusprd01.
- `backend/tests/test_products.py`: catalogue extensibility, scoped uniqueness,
  customer installation integrity, authorization and reversible migration tests.
- `backend/app/db/models/customer_context.py`: department/course/calendar tables.
- `backend/app/api/v1/endpoints/customer_context.py`: scoped registry and calendar API.
- `backend/app/api/v1/endpoints/registry.py`: session, autocomplete, routing and search context.
- `backend/app/services/product_search.py`: reusable same-product SQL ordering hook.
- `backend/app/registry_ui.py` and `backend/app/static/registry/`: same-origin UI.
- `backend/alembic/versions/cusprd05_customer_context.py`: reusable context migration.
- `backend/alembic/versions/cusprd03_contract_calendar.py`: contracts/calendar migration.
- `backend/alembic/versions/cusprd08_product_team.py`: nullable default team migration.
- `backend/tests/test_customer_context.py`: context, calendar, ranking and full migration checks.
- `backend/tests/test_registry_auth_ui.py`: actual login/JWT/RBAC and UI shell checks.
- `backend/tests/preview_registry.py` and `backend/tests/browser_registry.cjs`: isolated UI QA.
- `backend/requirements.txt`: adds missing form/email dependencies and constrains
  bcrypt to 4.0.1 because the existing Passlib bcrypt backend fails with version 5.

From backend, install `pip install -r requirements-dev.txt`, then run
`python -m pytest tests -q`. Apply schema with `alembic upgrade head`
before starting `uvicorn app.main:app --reload`. Explore `/docs` with an access JWT.
Tests isolate sessions using SQLite and do not run the existing startup seed.
MariaDB deployment and live JWT integration require the team's actual environment;
SQLite checks do not replace those staging checks. A new database should run
the Alembic chain before startup; the existing startup uses create_all.

Verified locally: 18 backend tests passed, covering the implemented registry scope.
Customer tests cover multiple channels, Thai/name/
channel search, duplicate handling, shared groups, validation, permissions,
unauthenticated access and migration upgrade/downgrade. Product tests cover
adding ExamPlus/GetA/Logbook and a fourth service, product-scoped modules,
multiple instances per customer, duplicate conflict rollback, scoped filters,
Admin-only catalogue writes, invalid URLs and product migration rollback/reapply.
The complete Alembic
chain also generated MySQL SQL successfully with `alembic upgrade head --sql`.
The complete upgrade chain emits MySQL SQL successfully through `cusprd08`.
Browser QA passed login, organization/contact/channel/product/module/instance
creation, department/course management, contract/calendar/team setup,
autocomplete auto-fill/stale-selection clearing and Auditor read-only controls.
The final browser run also verified that a delayed customer response does not
overwrite the product view after navigation.
The 390px mobile viewport had no document-level horizontal overflow; desktop
and mobile screenshots were inspected. No live MariaDB migration or deployment
has been performed. Upstream deprecation warnings remain in existing schemas.

Migration order: `fef2a1063bc1 -> cusprd01 -> cusprd02 -> cusprd05 -> cusprd03 -> cusprd08`.
The task number is a Jira reference, not a migration sequence; 03 follows 05
because exam windows reference departments. Apply `alembic upgrade head` once
after review. Downgrading removes the corresponding registry data; use backups
and the team's migration review process for real environments.
