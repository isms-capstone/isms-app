# CAT options and acceptance data — 2026-11-04

## Findings

The active backend is the Docker application mounted from `C:\Capstone\isms-app\backend`.
Its database had all eight active ticket types, including Request, but zero products,
customer product instances, symptoms, service stages, cause codes and solution codes.
An empty dropdown could not be corrected by selecting a different category in the UI.

## Changes

- Show separate messages for no customer selected, no instances linked to a customer,
  no product selected, and missing category/code configuration.
- Load global ticket types/codes independently of product-option failures.
- Keep the eight standard types in their familiar order, with Request third; personal
  saved usage still takes priority when using product-scoped options.
- Explain duplicate tags explicitly. Tags are normalized and case-insensitive;
  `QA-CAT-DOWNLOAD` and `qa-cat-download` represent one tag.
- Allow CAT edits on historical cases with legacy intake channels such as `WEB`.
  The existing channel is preserved; the capture API still validates new channels.
- Add the explicit, idempotent `backend/scripts/seed_cat_qa.py --apply` command.
  It adds only clearly labelled QA catalogue records, without changing existing
  customer associations, cases, credentials or inactive configuration. It is never
  invoked automatically at startup.

## Active local QA data

The seed was explicitly applied to the actual local backend: 17 records created.
A second execution created zero records, confirming idempotency.

Open `http://localhost:3100/cases/new`, log in as Admin and search for the customer
`QA CAT - ทดสอบหมวดหมู่`. Expand `รายละเอียดเพิ่มเติม` and use:

| Field | Value |
| --- | --- |
| Customer | QA CAT - ทดสอบหมวดหมู่ |
| Product instance | QA CAT Instance A · 1.0 · test |
| Type | Request or Issues |
| Module | Teacher or Student |
| Symptom | Download failure |
| Service stage | During exam |
| Problem type | Teacher access or Student access, matching the module |
| Cause | QA-CAT-CONFIG · QA CAT - ตั้งค่าระบบไม่ครบ |
| Solution | QA-CAT-RECONFIG · QA CAT - ปรับตั้งค่าและทดสอบซ้ำ |

Switching to `QA CAT Instance B · 1.0 · test` must clear the product-dependent
fields. Its choices are Clinic, Mapping error, General and Clinic access.
The original customers still require their real product-instance associations;
the QA catalogue is deliberately linked only to the QA customer.

## Verification

- Backend regression: **96 passed, 1 skipped**.
- Browser/contract suite with a separate MariaDB QA database: **18 passed**.
  Includes desktop 1440px, touch emulation 390px, Request fulfilment,
  severity matrix, tag feedback/report, history, personal frequency,
  missing customer configuration and product-option failure isolation.
- TypeScript and changed-file ESLint checks passed.
- Actual backend read checks confirmed both QA instances and all scoped/global options.
- Actual backend CAT GET/PATCH and popular-tag report returned 200;
  legacy and canonical WRK creation returned 201; unified timeline returned 200.
  These temporary API writes were rolled back and absence verified separately.
- The actual backend was restarted and reported healthy. Frontend port 3100 was
  left under the user's control; browser QA used port 3102.

Mobile coverage is browser touch emulation, not a claim of testing physical devices.
