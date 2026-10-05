# Shared ADM / CUS registry and task 07

Updated 2026-10-05 (Asia/Bangkok). ADM base: ffef73f; integration: bf737f8;
task 07 configuration: a4166fc. Implementation lives on feature/P1-CUSPRD.

## One active catalogue

- Canonical tables/models: `master_data.Product` -> `products`, and
  `master_data.Module` -> `modules`.
- `app.db.models.product.Product` / `ProductModule` are aliases, not second ORM
  models. Customer `product_instance.product_id` points to `products.id`.
- ADM and registry endpoints read/write the same IDs. ADM-created catalogue rows
  receive generated registry codes; database defaults also support older ADM
  writers that omit code columns. Registry-created rows are visible in ADM.
- Product code/default team are preserved from the legacy registry. Product
  names are unique and at most 150 characters; module names are at most 100.
- Customer editor roles are Admin, Agent and Team Lead; legacy User cannot write.
  Authenticated active users can read; catalogue/category/SLA writes are Admin-only.

## Migration and retained data

The existing CUS and ADM histories remain intact:

```
fef2a1063bc1 -> cusprd01 -> cusprd02 -> cusprd05 -> cusprd03 -> cusprd08
fef2a1063bc1 -> 8d2c4a1b7e90 -> c4e7f1a9b2d3
(cusprd08, c4e7f1a9b2d3) -> cusadm01 -> cusprd07
```

Run online `alembic upgrade head` against a reviewed/backed-up database.
`cusadm01` adds codes/team references to ADM tables, matches existing products
by name, imports missing products/modules, and remaps instance IDs. Existing
ADM active state is authoritative for matched rows. Database collation governs
matching. Duplicate/overlong legacy names are rejected for manual reconciliation;
no automatic truncation occurs. Generated codes avoid legacy-code collisions.

The old `product` / `product_module` tables and `cusprd_product_id_map` remain
rollback snapshots only. No running API writes or reads the old catalogue.
Rollback uses the saved mapping and refuses to roll back new canonical products
that already have instances without exporting/reconciling them first. Snapshots
represent pre-migration state; rollback is not a synchronization mechanism for
later edits. SQLite populated-data tests permit table rebuilds, then explicitly
check FKs; MariaDB CI verifies the migration with real FK enforcement throughout.
This data migration cannot run with `--sql` offline mode.

## Task 07 UI and API

Login as Admin at `/registry`, choose Product Registry and a product. Admin can
manage modules, symptoms, service stages and module-specific problem types;
choose/create an SLA policy and add/edit its severity rules. Changes use ADM APIs
and are visible on subsequent reads without restart. Deactivation preserves rows.
Different products can share a policy intentionally; editing its rules affects
all products using it. Create a separate policy for independent timings.

All paths are under `/api/v1`:

| Endpoint | Contract |
| --- | --- |
| GET /registry/sla-policies | Admin choices: active ADM SLA policies |
| PUT /products/{id}/sla-policy | Admin body `{ "sla_policy_id": id_or_null }`; unknown 404, inactive 409 |
| GET /products/{id}/case-options | Active product-scoped modules/symptoms/stages/problem types and active assigned SLA/rules |
| POST /products/{id}/validate-case-options | Validate selected module_id, symptom_id, service_stage_id, problem_type_id; extra fields rejected |

Missing SLA assignment is explicit null, with no invented fallback. If the assigned
policy is disabled, configured_sla_policy_id is retained and sla_policy is null.
Inactive products return 409 from case-options. Inactive category rows and problems
whose modules are inactive are omitted. Cross-product IDs or a problem type under
a different selected module return 422.

CAP must query case-options after selecting the product, clear previous choices on
product changes and validate ownership again during ticket writes. The HTTP validation
endpoint demonstrates the contract; final CAP writes must perform equivalent checks
inside their own transaction. The actual ticket table/form is absent on this branch,
so task 07's case-form acceptance is still pending. SLA execution remains SLA work;
this module stores configuration and exposes the policy/rules for that engine.

ADM-05 templates and ADM-06 rules were not added or changed. They do not block
registry configuration; future assignment rules should consume the existing
product routing-context/default team.
