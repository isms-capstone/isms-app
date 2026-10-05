# ADM / CUS / CAP compatibility audit — 5 October 2026

Scope: integrate the teammate's ADM branch into existing CUS/PRD and CAP work.
No new CAP task is started. No merge into develop/main or production migration is performed.

## Verified branch origins

- feature/P1-CUSPRD was created from origin/feature/P1-INFRA at 0b2ea25 (local reflog).
- ADM through ffef73f was integrated into CUSPRD by bf737f8.
- feature/P1-CAP was created from feature/P1-CUSPRD at 07fe675 (local reflog).
- This round incorporates origin/feature/P1-ADM at 74ef224 into feature/P1-CAP only.
  The standalone CUSPRD branch retains its previous head.

## Findings and fixes

- Four merge conflicts in Alembic model imports, model exports, route registration and
  master-data schema imports were resolved retaining both ADM and CUS/CAP behavior.
- The new ADM migrations ended at e3f4a5b6c7d8 while CAP ended at cap01.
  cusadm02 joins both histories without changing upgrade schemas or tables.
- MariaDB CI exposed ADM-06 rollback dropping a foreign-key-backed index too early.
  The integrated downgrade drops the automation_rules table directly, removing its
  indexes/FK together; upgrade behavior is unchanged.
- ADM-05 tests replaced app modules globally with stubs during collection. This could
  break other tests or bypass real dependencies. The integrated copy imports real
  dependencies and uses application-scoped FastAPI overrides instead.
- Registry SLA and Automation navigation now links to the existing ADM screen for Admin.
  This enables configuration access; it does not implement SLA execution or case routing.
- Products/modules/categories, SLA policy IDs, user roles and team IDs remain shared.
  No second master-data catalogue or separate team registry is created.

## Task comparison (task numbers follow the Phase 1 task document)

| ADM task | Evidence / compatibility conclusion |
| --- | --- |
| 01 users/teams/roles | Existing canonical users/teams/roles and authenticated roles remain compatible; JWT/RBAC regression covered. |
| 02 category axes | Capture and registry use ADM modules/symptoms/service stages and enforce product ownership. |
| 03 ticket types/cause/resolution codes | Shared ADM tables and CAP foreign keys remain intact; commit labels on ADM do not exactly match these task numbers. |
| 04 SLA/calendar | Shared policy/rules and product-policy capture snapshot remain compatible. SLA timers are separate work. |
| 05 templates/canned messages | New models/migrations/routes retained; template creation against registry-created product/module/category and authenticated selection verified. No template capture feature added. |
| 06 configurable rules | Teammate's management API/service retained; real JWT admin-only CRUD verified, existing active/disabled service tests pass. No new assignment workflow added. |
| 07 all-screen master-data acceptance | ADM source contains users/teams/roles/master/SLA/templates/automation screens. This audit verifies integration and APIs, not a complete manual acceptance run of every ADM screen; it does not certify this teammate task Done. |

ADM-06 currently supports equality conditions and assign_team actions. Its service consumes
product_id and problem_type_id; CAP stores product_instance_id and category_id. Future runtime
routing must resolve the product instance and map category_id to problem_type_id, then persist
the team through the owning assignment workflow. The current registry routing-context only
exposes the configured default team; it does not claim to execute rules. Priority execution
is the teammate's existing behavior: ascending priority/id with the last matching assignment
winning. This round leaves that contract and the teammate's task scope unchanged.

## Validation

Full local backend: 42 passed, 1 skipped (MariaDB-only test).
The integrated suite covers existing customer/product/capture functionality plus ADM-05/06.
New tests verify one Alembic head, all-branch upgrade/downgrade with SQLite foreign keys,
shared catalogue template selection and real JWT/RBAC for rule CRUD.
MariaDB upgrade/downgrade and browser regressions are verified by GitHub CI after push.
