# CAP operational UI polish — 5 October 2026

Branch: `feature/P1-CAP`, based on merged develop `104c7d4`.
Reference: team wireframes 01.png, 02.png and 03_New Case/03-Default.png.

## Changes

- Shared navigation uses local SVG line icons, a compact brand mark, account avatar,
  consistent spacing and restrained active states in the existing CI palette.
- My Work has compact action counts, queue tabs, a stronger subject/number hierarchy,
  priority/status/tier treatments, ownership indicators and compact draft rows.
- All Cases separates the existing case search from its queue table.
- Capture has a three-field hint, selected-customer treatment, icon channel buttons,
  optional-details section, sticky preview and bottom save/create controls.
- Desktop and 375px mobile layouts retain the existing data and manual-save flow.

This is a visual update of implemented screens, not implementation of remaining CAP
tasks. SLA counts/sorting, similarity scores, bulk actions and other unavailable
wireframe features are not represented with fabricated data or nonfunctional buttons.
The existing SLA-unavailable note and real ticket numbering behavior remain explicit.
The registry shell is shared with customer/product pages; ADM's separate page is unchanged.

## Verification

- `npm run lint:registry` passes; `git diff --check` passes.
- Existing `browser_registry.cjs` workflow passes against a fresh isolated QA DB:
  login, customer/product CRUD, contract/exam context, autocomplete, create/draft,
  inline draft edits, reported-time edits, mobile navigation and read-only role checks.
- Additional visual checks cover My Work, All Cases and capture at 1440px/375px;
  real search returns the expected case, channel selected state is correct, there is
  no document horizontal overflow on mobile and no browser JavaScript errors.
- Screenshots in ignored `backend/tests/ui-output/cap-*.png` were visually inspected.
- The local MariaDB app at port 3000 stays healthy. QA fixtures use a temporary SQLite
  service on port 8767 and do not populate the user's MariaDB database.

No migration, API behavior, deployment workflow or remaining task implementation changed.
