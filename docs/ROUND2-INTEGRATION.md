# Round 2 integration review — 27 October 2026

Target: develop. Preparation: integration/P1-round2. No deployment requested.

Preserved full histories of:
- feature/P1-CAP at 6b9da36 (Next.js, GET Design and CI palette).
- feature/P1-CORE at 112503f (lifecycle rules and actions; PR #4).
- feature/P1-CAP3,5,7,10,11 at 9968fed (attachments, resolution, follow-up and creation on behalf).

PR #5 targeted main and was closed without merge. Its branch is included here;
it is not silently dropped and develop is the only integration target.

## Conflicts and corrections

- Kept CAP's validated follow-up implementation (full customer/product context)
  instead of registering two handlers for the same URL. Kept CORE auto-close and
  all attachment handlers. No feature branches, tables or volumes were deleted.
- Both resolve/status APIs now use a shared lifecycle service. Reject unknown
  statuses, unauthorized participants, inactive/missing FK references, missing
  resolution details and reopen requests outside the exact 14-day window.
- Preserve pending-external and cancellation reasons and append lifecycle history;
  additive migration r2_lifecycle follows the existing attachment/asset migrations.
- Removed the frontend's invalid ESCALATED status action. Escalation is routing,
  not a new ticket status. Lifecycle actions use server-provided permissions and
  collect required fields. The ESC workspace will extend this after integration.
- Fixed peer frontend type/lint errors and aligned badges with the ISMS palette.
- Added regression tests for permissions, persistence, resolution and old reopens.

## Validation

Existing backend suite: 72 passed, 1 isolated-MariaDB test skipped locally.
Added integration regression suite: 3 passed. Next production build passed.
PR CI additionally runs migrated MariaDB, complete backend tests, both registry
browser suites and Next frontend browser flows. Merge only after checks pass.

## Remaining scope boundaries

Existing CORE automatic closure has a callable job; scheduled execution/admin
configuration must be integrated with the job infrastructure. Routing, tier
history, response timers and handovers belong to ESC-01..09. Work-log/email
communication belongs to WRK. Do not claim those are implemented by this merge.
Local user data is not reset or migrated as part of preparing this PR.
