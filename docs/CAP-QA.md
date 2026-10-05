# CAP implementation and QA — 5 October 2026

Branch: `feature/P1-CAP`, based on the verified `feature/P1-CUSPRD` at `07fe675`.
The CUSPRD branch is unchanged. These additions are on CAP; neither branch has been merged or deployed.

## Delivered in this round

| Task | Implementation | Status |
| --- | --- | --- |
| P1-CAP-01 | Ticket model/migration, SRS 10.2 fields, registry/ADM/user references, required indexes, atomic monthly number sequence | Implemented and QA passed; peer migration review remains required before merge |
| P1-CAP-02 | POST /tickets: incomplete → DRAFT without number; three minimum fields → NEW with DVHT-YYYYMM-NNNNN | QA passed; ready for Done within this task |
| P1-CUSPRD-04 | Organization case overview, all open cases via pagination, classified problem history sorted by frequency | QA passed; ready for Done |
| P1-CAP-09 | Capture shows selected customer's open cases; “เพิ่มเข้าเคสเดิม” opens that case | QA passed; ready for Done |
| P1-CAP-12 | Phone and face-to-face options create ordinary cases and appear in normal customer counts/history | Capture and counting QA passed; downstream KPI module must retain the same channel-neutral queries |
| P1-CAP-04 | Basic capture UI, registry picker, product categories, 375px layout and 44px controls | In Progress: real users must demonstrate creation within 30 seconds after 5-minute training |

CUSPRD-05/06 now work in the actual capture form and persist department/course/customer IDs.
CUSPRD-07 now supplies product categories to real cases and snapshots the active product SLA policy.
Cross-product categories are rejected. Changing/clearing the customer context clears category IDs.
Their previously pending capture integration is covered here. The SLA engine itself remains a separate task.

## API

All paths are under `/api/v1`, require an active JWT session, and writes allow Admin, Agent,
Specialist, Developer and Team Lead. The authenticated read policy follows the internal registry.

- `POST /tickets`: optional subject/description/channel, organization/contact, department/course,
  product instance/module/category/symptom/service stage, ticket type, timezone-aware reported_at.
- `GET /tickets`: organization_id, open_only, offset/limit.
- `GET /tickets/{id}`: case details.
- `GET /customers/organizations/{id}/case-summary`: open_count.
- `GET /customers/organizations/{id}/problem-history`: frequency-ranked paginated history.

Channel codes: line_oa, line_group, line_personal, portal, email, phone, face_to_face, other.
`contact_id` alone resolves its organization; conflicting customer references are rejected.
Inactive selections and references across organizations/products are rejected.
The server owns status/number/creator/owner/timestamps/SLA snapshot; client overrides are rejected.

`reported_at` defaults to current UTC and accepts offset-aware times within the previous seven days.
`created_at` is separate and immutable through this create API. Important exam windows are evaluated
at reported_at, with inclusive start/exclusive end and matching organization/department.
No SLA timers or severity escalation are implemented by this capture endpoint.

Open cases: NEW, IN_PROGRESS, PENDING_CUSTOMER, PENDING_EXTERNAL, REOPENED.
DRAFT and RESOLVED are not active work queues; RESOLVED remains available in problem history.
History groups product/module/problem type/symptom and includes resolved/closed cases;
DRAFT, DUPLICATE and CANCELLED are excluded. Unclassified groups are explicitly labeled.
There is no hard delete or arbitrary status-change endpoint.

## Schema decisions

SRS names map to canonical ADM references: ticket_type → ticket_type_id,
module → module_id, category_id → problem_types.id, symptom_code → symptom_id,
exam_stage → service_stage_id, root_cause_code → root_cause_code_id,
resolution_code → resolution_code_id.
`kb_article_id` is reserved as a nullable integer; its FK must be added with the Phase 5 KB table.
This avoids fabricating a KB implementation. master_ticket_id already references ticket.id.

Migration chain adds `cap01` after `cusprd07`; there is one head.
Monthly sequence uses a transactional upsert and row lock on MariaDB, or SQLite's write lock.
Number month follows Thailand UTC+7; DRAFT does not consume a number. No case-delete route
exists, and cancelled case numbers remain stored. Monthly capacity is 99,999 cases.

## QA

- Full local backend: **32 passed, 1 skipped** (the skipped test requires isolated MariaDB).
- Capture tests also run against the actual migrated MariaDB in GitHub CI.
- Frozen migration upgrade/downgrade, field/index/FK checks and existing registry preservation.
- Draft/minimum capture, unexpected fields, missing/inactive references, scope isolation,
  timezone/backdating, exam snapshots, active/inactive SLA snapshots, no delete endpoint.
- Twenty concurrent allocations without collisions, Thailand month boundary and monthly reset;
  the same concurrency test exercises MariaDB's upsert/locking in CI.
- Customer isolation, open/terminal status filters, frequency order, empty customers and pagination.
- Browser: real JWT login, organization/contact selection, department/course, product categories,
  phone/face-to-face case creation, persisted IDs, customer summary, existing-case navigation,
  read-only role and navigation race regression; 375px layout and touch target size.
- API latency test checks <500ms on normal test fixtures. This is not a production load benchmark.
- Local JS lint and git diff --check pass.

Verified code commit: `9d4b251`.
[CI passed all four jobs](https://github.com/isms-capstone/isms-app/actions/runs/37277240523):
registry-mariadb-tests, registry-ui-tests, customer-registry-tests, lint-and-test.
Local Edge autocomplete in the final round: 231ms. Browser CI uses Chromium.
The first CI browser run revealed test navigation before login completed; the final test
awaits login explicitly and the complete workflow passes.

## Next tasks

1. P1-CAP-03: PATCH draft API, five-second/on-blur autosave, recovery after reopening/offline retry.
2. P1-CAP-06: “งานของฉัน”, own draft list oldest first, inline edit and draft count (uses PATCH).
3. Finish P1-CAP-04 real-user timing acceptance.
4. P1-CAP-08: editing reported_at plus integration with SLA clock; create-time validation is ready.
5. P1-CAP-07: lifecycle RESOLVED transition with required-field errors (lifecycle module).
6. P1-CAP-05: evidence upload/storage, paste/drop/mobile camera (attachment module).
7. P1-CAP-10: follow-up case action plus actual REL follow-up-of relationship.
8. P1-CAP-11: create for a teammate, team validation, creator/owner separation in audit log.

Do not mark all CAP or all Phase 1 Done from this round. No automatic draft recovery,
state machine, SLA engine, attachments, REL links, assignment audit or real-user timing is claimed.

## Wireframe UI update

See [UI alignment QA](UI-WIREFRAME-QA.md) for the later shared shell, desktop/mobile
capture, explicit draft action and operational queue changes. CAP-03 autosave, CAP-06
inline editing and CAP-04 user timing remain open.
