# สรุป CUS/PRD: Requirement → Task → QA → Jira

ตรวจเมื่อ 5 ตุลาคม 2026 (Asia/Bangkok) จาก Requirement Spec หัวข้อ 8.9,
10.1–10.2, 15 และ Phase 1 PRD ของ P1-CUSPRD-01..09
โค้ดที่ยืนยันผล: `42a1a82`, branch `feature/P1-CUSPRD`

หลักฐาน: [GitHub CI ล่าสุดผ่านครบ 4 jobs](https://github.com/isms-capstone/isms-app/actions/runs/37264462685)
เอกสารประกอบ: [QA](CUSPRD-QA.md), [ADM integration](CUSPRD-ADM.md)

## คำว่าเสร็จในรายงานนี้

- **Done ตาม task**: implementation ครบ acceptance ของ task ปัจจุบัน และส่วนที่ทำมี QA ผ่าน
- **Done สำหรับ preparation**: registry/API/component เสร็จและ QA ผ่าน แต่ acceptance ที่ต้องใช้ฟอร์มเคสจริงยังต้องตรวจใน integration
- **ยังไม่ได้ทำ**: ไม่ได้มี implementation ของฟีเจอร์นั้น ไม่ใช้ผล QA ของโมดูลอื่นแทน

ตามขอบเขตที่ทีมตกลงให้นับงานเตรียมเป็นงานส่งมอบได้ ให้ปิดงาน preparation
และเก็บงาน integration เป็น ticket/subtask แยกที่เชื่อมกลับมา หาก Jira ยังเก็บ
acceptance เดิมทุกข้อใน ticket เดียวโดยไม่แยก scope ให้ 05/06/07 คง In Progress
จนผ่านฟอร์ม CAP จริง ไม่ระบุว่าครบทั้ง Spec แล้ว

## ตารางเทียบทุก task

| Task | Requirement | งานที่เสร็จและ QA ผ่าน | ส่วนที่ยังไม่ตรวจครบ | สถานะ Jira |
| --- | --- | --- | --- | --- |
| 01 | CUS-01 | Organization/Contact/หลายช่องทาง, ค้นหาชื่อ/ช่องทาง, permissions/validation/migration | ไม่มี implementation ค้างตาม task | Done |
| 02 | CUS-02, PRD-01/02 | ADM catalogue ชุดเดียว, product-specific modules, org instances/version/environment/URL, เพิ่ม product ผ่าน Admin UI โดยไม่เปลี่ยน schema | ไม่มี implementation ค้างตาม task | Done |
| 03 | CUS-03 | วันสัญญา, exam_window ต่อองค์กร/หน่วยงาน, เพิ่ม/แก้ผ่าน UI, timezone/range/ownership | SLA-06 ต้องนำปฏิทินไปใช้ แต่ไม่ใช่ acceptance ของ task 03 | Done |
| 04 | CUS-04 | ยังไม่ได้ทำ summary API/UI | แสดงเคสเปิดและประวัติปัญหาเรียงความถี่จากข้อมูลเคสจริง | To Do / Blocked by CAP |
| 05 | CUS-05 | Department และข้อความ Course/Exam ผูกองค์กร, reuse, context selector, duplicate/scope validation | PRD ระบุให้ฟอร์มสร้างเคสใช้ตัวเลือกจริงและเก็บ IDs | Done preparation; full ticket In Progress หากไม่แยก integration |
| 06 | CAP customer selection | Autocomplete, active filtering, context/auto-fill, UI component, clear stale IDs; local timing 204–216ms ในรอบล่าสุด | ใช้ใน CAP form จริงและทดสอบ timing ใน environment ที่จะใช้งาน | Done preparation; full ticket In Progress หากไม่แยก integration |
| 07 | PRD-03 | Admin UI category/SLA ต่อ product, shared ADM data, active filtering, ownership validation, isolation tests | เคสจริงต้องแสดง/บันทึกเฉพาะหมวดหมู่ของ product; SLA engine ใช้ policy | Done preparation; full ticket In Progress หากไม่แยก integration |
| 08 | PRD-04 | Admin ตั้งทีมเริ่มต้นจาก ADM teams และ routing-context ได้ | กฎอัตโนมัติอ้างทีมนี้เมื่อมีกฎ; Spec ทั้ง PRD-04 ยังต้องมีงาน rules/routing | Done ตาม task ปัจจุบัน: PRD เขียน “ถ้ามี” |
| 09 | PRD-05 | product_instance_id parameter/context, SQL preference hook คงผลข้าม product และเอกสาร SIM usage | ค้นหาเคสจริงใน SIM/KB ยังเป็นงาน downstream; Spec PRD-05 ยังไม่ครบทั้งระบบ | Done ตาม task ที่ระบุให้เตรียม hook |

## ผล QA ที่ใช้ยืนยัน

- Backend ชุดปกติ: 22 tests ผ่าน; MariaDB-only test ถูก skip ในเครื่องที่ไม่มีฐานทดสอบ
- MariaDB 11.4 job: migration สอง branch → catalogue ร่วม, seed ข้อมูลที่ IDs ต่างกัน,
  ตรวจ code/team/module/instance, ทดสอบ ADM writer ที่ไม่ส่ง code, downgrade ถึง base,
  upgrade ใหม่และ API workflow ทั้ง registry/category/SLA ผ่าน
- Browser: actual login, CRUD, calendars, team, categories, product SLA/rule, autocomplete,
  stale response handling, desktop/mobile และ read-only controls ผ่าน
- JWT/RBAC: expired token, refresh token, inactive user, สิทธิ์เขียนและ concurrent reads ผ่าน
- Lint และ registry schema comparison ผ่าน; Alembic มี head เดียว `cusprd07`
- โค้ด commit/push แล้ว; ยังไม่ได้ deploy หรือ migrate ฐานลูกค้าจริง

QA ของ isolated registry ไม่ใช่ UAT ของฟอร์มเคสหรือ SLA/routing/search ทั้งระบบ
เวลาที่วัดในเครื่องไม่ใช่ผล load test ของ server จริง

## ขั้นตอนต่อไปตาม dependency ของ Spec

1. **ใช้ shared registry/ADM เป็นฐาน** — งานเตรียมตอนนี้พร้อมแล้ว ผู้พัฒนา CAP/CAT/ESC
   ต้องใช้ Product/Module IDs จากทะเบียน ADM ชุดเดียวกัน
2. **P1-CAP-01: schema ticket** — ผูก organization/contact, product_instance,
   module, department/course_or_exam และ category IDs ตาม Spec 10.2;
   ข้อมูล department/course ไม่ใช่ฟิลด์บังคับตอน Quick Capture
3. **P1-CAP-02 และ P1-CAP-04: create API + form** — ใช้ customer autocomplete,
   selection-context และ department/course choices; สร้าง DRAFT/NEW จริง
   เก็บงาน integration ของ CUSPRD-05/06 ในขั้นนี้
4. **P1-CAT-01: cascading categories** — product เปลี่ยนต้องล้างตัวเลือกเดิม;
   ใช้ case-options และตรวจ product/module ownership ใน transaction บันทึก ticket
   เก็บ integration ของ CUSPRD-07 ในขั้นนี้
5. **ทำ CUSPRD-04 กับ P1-CAP-09 เมื่อมี ticket** — ใช้ข้อมูลเดียวกันแสดงเคสเปิด;
   กำหนดสถานะที่นับว่าเปิดและวิธีนับปัญหาพบบ่อย แล้วทดสอบการแยกองค์กร/ความถี่
6. **P1-ADM-06 + ESC** — เมื่อกฎอัตโนมัติพร้อม ให้อ้าง default team/routing context
   ของ CUSPRD-08; ต้องตรวจผลมอบหมายบนเคสจริงเพื่อปิด requirement PRD-04 ทั้งระบบ
7. **SLA engine / P1-SLA-06** — รับ policy ตาม product, ใช้ reported_at และ
   organization/department exam_window ในกฎยกระดับพร้อมแจ้งหัวหน้าทีม
8. **SIM** — รับ product_instance_id และใช้ ordering hook ของ task 09 ก่อน pagination;
   QA ด้วยเคสจริงว่า product เดียวกันขึ้นก่อนและยังค้นข้าม product ได้

บางขั้นทำขนานได้หลัง schema/contract ของ ticket ชัดเจน ไม่จำเป็นต้องรอ
ทุกโมดูลเสร็จตามลำดับเดียวกันทั้งหมด CAP/CAT/SLA/ESC/SIM อยู่ Phase 1
เช่นเดียวกับ CUS/PRD; เป็นคนละรอบงาน ไม่ใช่ต้องรอ Phase 2/5

## เลข requirement กับเลข Jira task ไม่ใช่เลขชุดเดียวกัน

- P1-ADM-01 task ผู้ใช้/ทีม/บทบาท รองรับ ADM-01 ของ Spec
- P1-ADM-02/03/04/05 task master-data หลายประเภท แตกจาก ADM-02 ของ Spec
- **P1-ADM-06 task กฎอัตโนมัติ รองรับ ADM-03 ของ Spec**
- ADM-05/06 ใน Spec เป็นการนำเข้าข้อมูลเก่าและเก็บ legacy_case_no ใน Phase 5
  ไม่ใช่ task P1-ADM-05/06 เรื่อง template/rules

ไม่ต้องรอ task P1-ADM-05 เพื่อส่งมอบ registry ส่วนปัจจุบัน และ task 08
ไม่จำเป็นต้องรอ P1-ADM-06 เพราะ acceptance ของ task ใช้เงื่อนไข “ถ้ามี”
การเชื่อมกฎภายหลังยังต้องติดตามเพื่อให้ requirement ทั้งระบบครบ
