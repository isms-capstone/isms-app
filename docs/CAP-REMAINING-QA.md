# Existing CAP work completion — 5 October 2026

Scope agreed with the user: finish only previously started CAP-04, CAP-06 and CAP-08.
No ADM implementation, autosave, attachments, lifecycle, follow-up or delegation task is added.
Branch: feature/P1-CAP. No merge into develop/main has been performed.

## CAP-06 — completed implementation and QA

My Work displays all own drafts through pagination, oldest first, with a visible total.
Each draft supports explicit one-field inline edits for subject, description, channel,
organization/contact, department/course, product instance, module/problem/symptom/stage
and ticket type. Edits stay on the queue without opening a full capture form.
The mobile list becomes readable rows at 375px, with 44px edit controls.

PATCH /api/v1/tickets/{id}/draft-field accepts exactly a field and value. Only the creator,
with an existing capture editor role, can edit DRAFT records. Arbitrary state/number/user
changes are rejected; editing a draft never issues a number or automatically publishes it.
Parent changes clear dependent context. Existing registry category validation is reused.
created_at/reported_at are preserved, including old drafts; SLA policy snapshots are only
updated when the selected product instance changes. Saves use a database row lock on MariaDB.
This API is explicit manual editing, not CAP-03 autosave/recovery.

Commit: ac4ace1.

## CAP-08 — capture/edit side complete; SLA acceptance pending downstream

PATCH /api/v1/tickets/{id}/reported-at accepts an offset-aware reported_at within the
previous seven days, rejects future/older/naive times and arbitrary fields, and stores UTC.
Admin or a capture editor who created/owns/is assigned to the case can edit the time.
The UI labels customer-reported time separately from immutable system creation time.
Editing does not change status, number, created_at or existing SLA policy snapshot.
The exam-window snapshot is reevaluated against reported_at.

The PRD's final acceptance requires all actual SLA calculations to start from reported_at.
There is no SLA calculation engine in this codebase, so that criterion cannot yet be
verified. The fields/API are ready for the owning SLA module. Do not mark the whole
CAP-08 task Done solely from this capture-side implementation.

Commit: a1d0517.

## CAP-04 — implemented/browser QA; real-user timing pending

The 375px Quick Capture form and 44px channel/submit controls are covered by browser QA.
The PRD explicitly requires a real person trained for five minutes to create a case
within 30 seconds. Automated browser timing does not satisfy that acceptance.
The user has been asked for a real tester's initials/name and measured elapsed seconds.
No result is fabricated and this task remains awaiting that evidence.

Training/test procedure:
1. Use the isolated QA app, not a file-system index.html. Log in as qa-agent using
   test-only-password. Never use this QA account on production.
2. Spend five minutes practicing Create Case: search TU, select the customer/contact,
   enter a short subject, choose a channel, submit and locate the issued case number.
3. Start a fresh attempt at the Create Case click; stop when the successful case number
   is visible. Record tester, device/width, training duration, elapsed seconds and errors.
4. Pass only with complete successful capture at <=30 seconds; keep the result as evidence.

## QA evidence

- Full local backend: 45 passed, 1 skipped (isolated MariaDB test); final targeted capture suite: 13 passed.
- Tests verify own-draft permission/status restrictions, field/type/scope errors, dependent ID
  clearing, unchanged timestamps, old draft editing, timezone normalization, seven-day/future
  rejection, immutable creation time and exam-window reevaluation.
- Local Edge browser: existing registry/capture regressions plus explicit draft editing on
  desktop and 375px mobile, mobile overflow check, and reported-time edit persistence.
- Screenshot draft-inline-mobile.png inspected; subject and editor remain readable without
  squeezing a desktop table. Final autocomplete: 210ms on isolated fixtures.
- JavaScript lint and git diff --check passed.
- Code/test commit 8af1d12 passed all four CI jobs, including migrated MariaDB capture
  tests and Chromium UI tests: [CI run 37295148758](https://github.com/isms-capstone/isms-app/actions/runs/37295148758).
  The reported-time fixture uses seconds to match MariaDB DATETIME precision.
