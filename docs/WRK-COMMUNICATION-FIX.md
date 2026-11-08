# WRK communication compatibility fix — 2026-11-03

## Follow-up: runtime 500 incorrectly displayed as 502

The next report was traced through the actual container logs. Its ORM models
`TicketWorklog.ticket_id` and `TicketStatusHistory.ticket_id` referenced
`tickets.id`, while both the `Ticket` model and the real MariaDB foreign keys
reference `ticket.id`. SQLAlchemy raised `NoReferencedTableError` before insert.
The backend returned plain-text HTTP 500; the BFF attempted `response.json()`
and incorrectly converted that parse failure into a connection-error 502.

The two incorrect ORM references were changed to `ticket.id` in the running
checkout's `backend/app/db/models/ticket_history.py`. The original file was
backed up in the workspace before the exact two replacements. Only the local
application container was restarted; no database migration or reset was run.

Verification used the actual checkout's FastAPI routes and real MariaDB inside
an outer transaction with savepoints: Internal Note returned **201**, and Public
Reply with `line_oa` returned **201**. The outer transaction was rolled back and
a separate connection verified that no QA messages remained. The running
application's health endpoint returned **200** after restart.

The BFF now preserves non-JSON server-error status codes and returns a safe
message instead of claiming the backend cannot be reached. Tracebacks are not
sent to the browser. Unparseable successful replies ask the user to reload the
timeline before retrying, since persistence cannot be inferred from the reply.
Regression tests include a plain-text backend 500, preserving the draft, and
one successful insert after an explicit retry. The updated legacy browser and
contract profile passed **13 tests**.

The original compatibility work below remains necessary for the API-schema
difference, but its mock-backend QA alone did not cover this ORM fault.

## Confirmed cause

The Next frontend in `C:/Capstone/isms` connects to port 3000. Read-only inspection
of the running Docker container showed that this backend is mounted from
`C:/Capstone/isms-app`, a separate checkout. Its actual OpenAPI exposes
`GET/POST /api/v1/tickets/{ticket_id}/worklogs`, with the request fields
`message`, `is_internal`, and `channel`. It does not expose `timeline` or
`categorization`.

The frontend sent `kind` and `body` to that backend, producing 422. Requests to
the two absent routes produced 404. This is a deployed API contract mismatch,
not a reason to delete data, stamp migrations, or overwrite the other checkout.

## Change

- The existing authenticated Next BFF reads and briefly caches the backend's
  OpenAPI capabilities. It maps WRK writes to the observed legacy schema or
  preserves the canonical `kind/body` schema supported by this branch.
- Legacy worklogs are normalized into the UI's message type, actor, UTC timestamp
  and actual public delivery channel. Internal notes never display the legacy
  default intake channel as if they were externally delivered.
- When the connected backend has no unified timeline, the BFF returns an ordered,
  paginated communication feed from its authorized worklog endpoint. The UI labels
  this limitation; it does not invent missing lifecycle events.
- Category and Request panels check capabilities before requesting unsupported
  endpoints. This does not install CAT functionality into the other checkout.
- A successful save inserts the server-returned record into the timeline
  immediately, without a page reload or a second request. The record uses the
  server's ID, actor and time. Loading more history uses a separate paging offset
  and deduplicates IDs, so saving beyond the first 100 entries does not hide the
  new record or skip older entries.
- The LINE OA selector has an explicit accessible label. Public Reply retains
  the green border and `ส่งจริงผ่าน LINE OA` label.
- Worklog payload validation rejects blank content, invalid/missing public
  channels, external channels on internal notes, and spoofed actor fields before
  forwarding to a legacy backend. Existing authentication and write-Origin
  checks remain in place. There is no retry of a failed POST with another schema.

This follow-up fixes the reported WRK behavior. It adds no new frontend design or
unrelated product feature, and does not modify the running backend checkout,
its accounts, migrations, or real tickets.

## QA executed

The tests start services on loopback ports 8878 and 3102, with a separate Next
build directory. They do not write to the user's running port-3000 database.

- Legacy-contract profile: **10 passed**. This includes 8 contract/validation
  tests, one browser save/reload test, and one browser test with 105 existing
  worklogs.
- Canonical-backend profile: **9 passed**, using the actual FastAPI routers,
  temporary SQLite database, existing JWT login and the real Next BFF.
- Browser assertions verify immediate Internal Note insertion; Public Reply
  with LINE OA; exact delivery label; computed green border color; persistence
  after reload; no reported 404/422 on the valid legacy flow; and no duplicate
  or skipped records when paging after saving. The legacy profile also checks
  mobile horizontal overflow.
- Frontend TypeScript typecheck and ESLint pass.

Full CAT browser acceptance, live MariaDB validation and a production build are
not claimed by this WRK follow-up. Public Reply records an already-sent message;
it does not send a LINE message itself.

To repeat on Windows after installing the existing dependencies:

```powershell
cd frontend
$env:WRK_QA_PYTHON='C:\Capstone\isms\.venv\Scripts\python.exe'
npm run test:worklog-compat
$env:WRK_QA_FORMAT='canonical'
npm run test:worklog-compat
```

The legacy profile is a disposable fixture matching the observed wire contract.
The canonical profile uses `preview_registry.py`. The regular test configuration
skips these profile-specific browser tests. Next dev may regenerate
`next-env.d.ts` and add its temporary type paths to `tsconfig.json`; the normal
workspace type paths were restored after verification.
