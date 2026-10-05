# Wireframe UI alignment — 5 October 2026

Branch: feature/P1-CAP. Source: the provided Wireframe images/PDF and six-color palette.
This is an implementation update of existing pages, not a claim that every Figma frame is finished.

## Changed

- Shared palette: #060B0F text, #33454E navigation/actions, #76949F metadata,
  #FBF5F3 background, semantic #73E8AF success and #9E2A2B critical/error states.
- Fixed desktop sidebar with grouped navigation, real product entries from ADM,
  collapse/drawer interaction, current user identity and Admin-only navigation.
- 56px top bar, breadcrumbs, create action, compact 6–8px surfaces and tables.
- First screen My Work: real unassigned/my-assigned/today counts and own draft count.
  My active work means Assignee = Me, not Creator = Me.
- All Cases/Unassigned: real paginated cases and number/subject search, case detail links,
  customer/product names, status/channel/tier and honest unavailable SLA state.
- Mobile queue transforms into readable case rows rather than squeezing desktop columns.
- Capture: three minimum fields, selected customer, channel buttons, collapsible enrichment,
  live preview and a persistent action bar; no raw JSON or speculative case numbers.
- Separate save-as-draft and create actions. Complete information can still be saved as DRAFT
  explicitly; normal complete capture becomes NEW. Writes are guarded against double clicks.
- Department/course/product categories still persist via the existing validated API.
- Preview uses current selections. Changing customer clears customer-dependent IDs.
- Default empty existing-case list uses a compact message; real open cases remain accessible.
- Dynamic product nav refreshes after catalogue changes; unavailable modules are disabled.

## QA

Full local backend: **33 passed, 1 skipped** (isolated MariaDB-only test).
Targeted capture/queue tests verify explicit complete DRAFT, minimum NEW, Assignee = Me,
creator-scoped drafts, counts, search escaping, validation and existing capture invariants.
Existing backend regressions remain covered by the full CI suite.

Browser QA uses actual JWT login and API writes. It checks desktop/mobile capture, expanded
context/category fields, NEW and explicit DRAFT responses, selected ID persistence, clearing,
existing-case navigation, own drafts, four action counters, 375px layout, menu drawer,
44px submit control, exact sidebar color, 56px header and read-only role behavior.
JavaScript lint and git diff --check pass. Desktop and mobile screenshots were inspected.

Screenshots are generated under backend/tests/ui-output and uploaded as CI artifacts.
They are QA fixtures, not production customer data.

## Remaining acceptance / downstream work

- SLA clock/risk/time-remaining order: unavailable until the actual SLA engine is integrated.
  UI shows unavailable state and explicitly labels current creation-time ordering.
- CAP-03 autosave/recovery and CAP-06 inline draft edit remain unfinished; drafts can be viewed.
- CAP-04 still needs trained real-user timing <=30 seconds; browser layout is not that user study.
- SIM suggestions, evidence/OCR, lifecycle/worklog timeline, advanced search/filter drawer,
  complete product operations pages and full redesign of the existing ADM app remain separate work.
- No fake counts, urgency, similarity scores, notifications, SLA timers or demo personas are inserted.

## Git

441b9e8: explicit draft and queue API support.
f8f9437: My Work uses assignee semantics.
c10db3b: shared shell and responsive capture visual update.

All four CI jobs passed for code commit c10db3bfe2809aa6b02d58cca484d7ed07e5a340:
[GitHub Actions run 37287245352](https://github.com/isms-capstone/isms-app/actions/runs/37287245352).
The final local Edge browser QA passed; customer autocomplete completed in 230 ms.
