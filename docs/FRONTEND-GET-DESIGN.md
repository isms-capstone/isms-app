# Frontend — GET Design integration

This frontend-only branch starts from develop (7b31a21). ESC backend, migrations, worker, routing pages and routing tests remain in PR #7 and are excluded.

Uses official @DeverhoodHT/get-design 1.5.2, GetX/light tokens, bundled Noto Sans/Thai fonts and shared buttons, inputs, selects, search, tags, tables and summary cards. Sidebar: light blue #EDF4FF, navy text and blue selected states.

Reference: https://pages.dev.deverhood.com/get-design-27f42e/?path=/docs/docs-getting-started--docs

Shared adapters preserve form submission, validation and keyboard behavior. Existing develop workflows remain intact. No migration or database reset is needed.

Rebuild with the existing docker-compose.yml, docker-compose.override.yml and docker-compose.frontend.yml overlays. Open http://localhost:3100/preview/my-work or /login.

## Verification — 3 November 2026

Frontend lint and production build (including TypeScript) passed. All four browser tests passed against the unchanged develop backend with a disposable database: desktop/mobile previews and filters, login/case creation/draft editing/logout, cross-origin and authorization checks, read-only denial/error recovery/empty search.
