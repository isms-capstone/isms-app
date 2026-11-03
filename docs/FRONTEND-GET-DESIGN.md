# Frontend — GET Design adoption

Branch: `feature/P1-frontend-get-design`, based on `feature/P1-ESC` so existing ESC work remains available. Frontend review should compare against that base until ESC is merged. This change does not merge or deploy either branch.

## Official reference

Storybook: https://pages.dev.deverhood.com/get-design-27f42e/?path=/docs/docs-getting-started--docs

The application now pins `@DeverhoodHT/get-design` **1.5.2**, matching the Storybook version inspected on 3 November 2026. It uses **getx / light**, the company's blue brand palette, semantic success/warning/danger colours, and the library's bundled **Noto Sans / Noto Sans Thai** fonts. This supersedes the previous custom six-colour ISMS theme at the user's request.

## Adoption

- Official Button filled/outline/plain, Checkbox, Toggle, TextInput, SecureInput, Search, Select, Tag, Segment, StatCard, EmptyState, Skeleton and table cells/header cells.
- Shared adapters in `frontend/src/components/ui/` keep the existing application API and avoid deprecated InputText/InputTextarea components.
- All React dropdowns and multiline fields in capture, queues, case detail, lifecycle and ESC use the company components. Native number/date-time/file controls remain where their browser semantics are needed.
- Shell, surfaces, navigation, tables and status treatments consume the library's public colour tokens. `company-theme.css` maps application aliases; it does not redefine the company's palette or font tokens. `company-layout.css` contains application composition and consistent operational control typography.
- Toolbar buttons, dropdowns and fields use the official 42 px medium size. Small icon/pagination actions use the official small size. Responsive table/card behavior and the original logo remain.

## Integration details

The company Select uses a hidden native select for form submission and a custom visible trigger/menu. `SelectControl` preserves names, required validation, controlled/uncontrolled values and native FormData. It mirrors the label to the visible trigger for screen readers and keyboard users, focuses it on invalid input, and prevents a containing label from synthesizing a second click on the hidden select that would immediately close the menu.

Browser tests click the visible option menu instead of assigning the hidden select's value. Admin tests still verify persisted routes, leaders and tiers; ESC tests still verify required context, ownership, nested return, availability, bulk handover, lifecycle and read-only permissions. Colour/size assertions now check GetX tokens and the company medium-size controls.

## Local usage

Use the existing Docker Compose overlays and database. Rebuild the frontend after pulling:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.frontend.yml -f docker-compose.routing.yml up -d --build --wait frontend
```

Open http://localhost:3100/preview/my-work for visual reference, or /login for actual persisted workflows. Never reset the database to apply this UI update.

The older standalone backend Admin/Registry pages remain separate applications; this change targets the Next.js frontend rather than rewriting another team's legacy pages.

## Verification — 3 November 2026

- Frontend lint, TypeScript and Next.js production build passed, including the Docker build.
- Production dependency audit: zero vulnerabilities (`npm audit --omit=dev`).
- Real Edge browser suite: **9 passed, 1 skipped** against a fresh disposable API database. Covers desktop/mobile previews, filters, real login/capture/drafts, failure/empty recovery, read-only denial, ESC handoff/return, self-assignment, availability switch, workload handover, Admin forms and complete nested return before resolution.
- The opt-in five-minute scheduler scenario is skipped in this frontend-only run; the worker and routing backend are unchanged. Its real-time acceptance evidence remains in the ESC report.
- Existing local Docker database is retained. Frontend 3100 and backend 3000 respond successfully; the existing routing worker remains running.
- Local screenshots, video and traces are retained outside Git under `../output/frontend-get-design-2026-11-03/`.
