# ISMS Frontend

Next.js App Router, TypeScript, Tailwind CSS 4, Sarabun Thai font and Lucide icons.
The company logo is the original user-supplied asset in `public/brand/`.

## Run locally

The existing Backend and MariaDB must be running and migrated (root README).
This frontend uses port **3100**; Backend remains on **3000**.

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

For a production build locally: `npm run build`, then `npm start`.
`scripts/start.mjs` prepares static assets and starts Next's standalone server.
Open `http://localhost:3100/login` with your existing ISMS account.
No credentials are hard-coded into the frontend. New local DB accounts are documented
in the existing backend setup. A database with existing accounts preserves their passwords.

Alternatively, from repository root:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.frontend.yml up -d --build frontend
```

The optional overlay adds only a frontend service. It does not run migrations,
replace server deployments, delete volumes or change the backend/database credentials.

## Routes and components

- `/my-work`: action counts, queue, filters, drafts and manual inline draft subject editing.
- `/cases`: search, selectable rows, filter drawer, pagination and CSV export.
- `/cases/new`: customer/contact autocomplete, minimum capture, optional existing
  context/catalogue fields, Draft/New saves and live preview.
- `/cases/[id]`: current case information, own draft text/channel edits and permitted reported-time edits.
- `/unassigned`, `/products/examplus`, `/products/geta`, `/products/logbook`: queue scopes.
- `/customers`: searchable customer list. Full CUS/PRD CRUD remains available through
  the explicit registry link. Existing `/registry` and `/admin` are proxied to Backend;
  they retain their own login flow during this frontend migration.

Shared shell lives in `src/components/layout`; feature components in `cases`, `capture`
and `customers`; primitives in `ui`. CI palette is centralized in Tailwind `@theme`
and semantic CSS tokens in `src/app/globals.css`. Component code is formatted with Prettier.

## Company component library

Requested source: https://gitlab.dev.deverhood.com/deverhoodht/design/get-design.git

Uses **`@DeverhoodHT/get-design` 1.0.7**, verified against the authenticated company
repository README and the published package's TypeScript declarations/source. The
committed `.npmrc` scopes only this company's packages to its documented GitLab npm
registry. The package registry permits installation without a token; no credentials
or browser sessions are stored in the project, lockfile, Docker image or CI config.

Actual company components used: `Button`, `InputText`, `Checkbox`, `TableHeaderCell`,
`TableCell`, `Tag`, `Skeleton` and `LanguageProvider`. `components/ui/primitives.tsx`
adapts their typed APIs to compact operational controls. Public table cell helpers
preserve the bespoke desktop/mobile layouts and native table semantics; they are
the library's documented option for composing a custom table.

The official package stylesheet loads before product CSS. `<html>` sets the required
`data-color-set="getx"` and `data-theme="light"`, with Thai language context.
`src/styles/company-theme.css` maps the company's semantic colour/font tokens to
ISMS's six CI colours; original GetA brand colours do not override ISMS's palette.
The small, explicitly scoped component selectors in `globals.css` only adjust density,
layout, hit areas and font sizing. The InputText adapter enforces actual native
`maxLength` via the package's character-count variant while hiding its optional counter.
Upstream library styles stay in node_modules and are never modified.

Next/Turbopack compatibility: the published 1.0.7 CSS has six invalid quoted `var()`
values in unused `*-ref` debug metadata. `scripts/postcss-company-compat.cjs` removes
only those declarations, only from the company's stylesheet, before Tailwind/Next
parse it. Actual design tokens and component rules stay intact. This is not a
patch to installed package files or a global relaxation of CSS validation.

## Real data versus design preview

`/preview/my-work`, `/preview/cases` and `/preview/cases/new` reproduce the supplied
wireframe examples without login. A persistent banner identifies design fixtures.
These routes never write fixtures to the backend. They include the reference SLA
states/counts and related-case examples for visual review.

Authenticated routes load real data only. Current Backend has no SLA countdown,
similarity, attachment upload, assignment/status/priority mutation or saved-view API.
Accordingly, unsupported controls are disabled/explained; real SLA shows unavailable,
and sorting uses actual creation time until SLA data becomes available. No SLA engine
or remaining CAP backend task was implemented as part of this frontend request.
Filters operate on the complete paginated API result, not just the displayed page.
Larger datasets should move filters/sorting/counts to server-side query endpoints later.

## Authentication

The Next server exchanges credentials with the existing FastAPI login endpoint.
Access tokens live in an HttpOnly, SameSite=Lax cookie for at most one hour; no token
is exposed through browser storage. All BFF writes validate the request Origin against
the incoming Host/protocol. Backend JWT/RBAC remains the authority. Session expiry
returns the user to login. Keep `BACKEND_URL` server-only, and deploy HTTPS before
using real accounts beyond local development. Production deployment remains manual.

## QA

```powershell
npm run lint
npm run typecheck
npm run build
npm audit --omit=dev
```

`npm run test:e2e` expects a disposable QA API on port 8767 and frontend on 3101:

```powershell
# Repository root, separate terminal (temporary SQLite fixtures; not the real DB)
docker compose run --rm --no-deps -p 127.0.0.1:8767:8767 app python -m uvicorn preview_registry:app --app-dir tests --host 0.0.0.0 --port 8767

# Frontend terminal after build
$env:BACKEND_URL='http://127.0.0.1:8767'
$env:PORT='3101'
$env:HOSTNAME='127.0.0.1'
npm start

# Another frontend terminal
$env:PLAYWRIGHT_CHANNEL='msedge' # Windows; omit for Playwright Chromium in CI
npm run test:e2e
```

Tests cover real API persistence, HttpOnly login/logout, CSRF/auth checks, filters,
SLA preview ordering, drawer keyboard dismissal, responsive overflow and screenshots.
Generated screenshots/traces are ignored under `test-results` and `playwright-report`.

Dependency audit at implementation: production dependencies have zero reported
vulnerabilities. Development lint tooling has an upstream braces advisory propagated
through eslint-config-next/fast-glob. The registry has no patched braces release;
do not force-downgrade Next or suppress the advisory to make an audit green.
