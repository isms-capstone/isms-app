# SIM + frontend/WRK/CAT ล่าสุด: การเปลี่ยนแปลงและ QA

ตรวจวันที่ 5 พฤศจิกายน 2569 — เก็บงานในเครื่องเพื่อรีวิว ยังไม่ push หรือ deploy

## ฐานโค้ด

- SIM เดิม: `feature/P1-SIM+oldfunc` ที่ `1f6dc12`
- frontend ที่รวมใน develop: `a2406ae`
- WRK/CAT ซึ่งรวม frontend ใหม่แล้ว: `WRK01-02+CAT01-07` ที่ `f637dc1`
- สำเนารวมงาน: branch ภายในเครื่อง `review/sim-oldfunc-latest`

main ของ repository ยังเป็นโครงเริ่มต้น จึงใช้ develop และ WRK/CAT ล่าสุดเป็นฐานจริง งานรอบก่อนในโฟลเดอร์ `isms-app-review` เก็บแยกไว้

## สิ่งที่ปรับให้เข้ากัน

1. ใช้ GET Design 1.5.2 และ SelectControl/TextArea ชุดใหม่กับแผง SIM รวม layout มือถือ
2. นำข้อมูลใช้ซ้ำเข้า CategoryFields และตรวจ impact scope, ช่วงสอบจริง และเหตุผล override Severity ด้วยกฎ CAT ชุดเดียวกัน
3. ใช้ `ticket_worklogs` และ `ticket_audit` ล่าสุด ไม่เพิ่ม Worklog อีกชุดหรือ endpoint ซ้ำ
4. แสดงการตัดสินใจ SIM ใน unified timeline และตัดเหตุการณ์สร้างเคสซ้ำที่เดิมแสดงเป็น NEW → NEW
5. คง oldfunc ที่เกี่ยวข้อง: สร้างแทนเพื่อนร่วมทีม, แนบไฟล์, แก้ intake ของเคส NEW, lifecycle และป้ายสถานะ
6. รวม migration SIM และ WRK/CAT เป็น head เดียว `simwrk02_latest` โดยเก็บ Worklog เก่าและสร้างดัชนีค้นหาของเคสเดิม
7. รักษาน้ำหนักลูกค้า/ผลิตภัณฑ์เดียวกันเมื่อคะแนนแสดงผลชน 100% และใช้ context ตั้งแต่การเลือก candidate ก่อนจำกัดจำนวน
8. แยก connection ของฐานทดสอบ SQLite ให้เหมือนระบบจริง เพิ่ม regression ว่า reader ที่ timeout ไม่ rollback งานสร้างเลขเคส
9. เพิ่ม `npm run test:sim-qa` และขยาย CI ให้ตรวจ SIM/Worklog บน MariaDB และ canonical WRK browser flows

## QA ตามงานเดิม

| Requirement | ผลในขอบเขต Phase 1 | สิ่งที่ตรวจ |
| --- | --- | --- |
| SIM-01 | ผ่าน | ต่ำกว่า 10 ตัวอักษรไม่ค้น, debounce 500 ms |
| SIM-02 | ผ่าน | เคสเปิด/ปิด; source-provider hook สำหรับเพิ่ม KB/Known Issue ใน Phase 5 |
| SIM-03 | ผ่าน | สูงสุด 5 ผลลัพธ์ พร้อมคะแนน แหล่ง สถานะ ผู้รับผิดชอบ ลูกค้า วันที่ล่าสุด |
| SIM-04 | ผ่าน | ป้ายวิธีแก้เดิม/กำลังดำเนินการ/ยังไม่มีผู้รับผิดชอบตามข้อมูลจริง |
| SIM-05 | ผ่าน | ยืนยัน 3 ทางที่ UI/API รวม Draft → New; link สร้างความสัมพันธ์จริง |
| SIM-06 | ผ่าน | เติมผลิตภัณฑ์ หมวดหมู่ Severity วิธีแก้ แก้ทับได้; ตรวจ instance ของลูกค้าปัจจุบัน |
| SIM-07 | ผ่าน | MariaDB FULLTEXT + PyThaiNLP และน้ำหนักลูกค้า/ผลิตภัณฑ์ รวมคะแนนชน 100% |
| SIM-09 | ผ่าน | ข้อเสนอ/การเลือกผูกกับ ticket_id และ audit; กัน feedback ของคนอื่น/ผิดเคส/ข้อมูลเก่า |
| SIM-10 | ผ่าน | timeout 1.5 วินาทีเงียบ ๆ; การค้นหาล้มเหลวไม่ทำลาย transaction สร้างเคส |
| SIM-11 | ผ่าน | ค้นซ้ำในหน้าสร้าง/รายละเอียด; API ตรวจทุกสถานะด้านล่างและไม่เสนอเคสตัวเอง |
| WRK-03 | ผ่านด้าน payload/สิทธิ์ API | SQL กรอง Internal Note ออกจากข้อมูล Portal/LINE/อีเมล; บทบาทลูกค้าเข้าถึง API ภายในไม่ได้ |
| WRK-04 | ผ่าน | Worklog ทุกครั้งมี actor/time/kind/channel/worklog_id ใน ticket_audit พร้อมกัน และแสดงใน timeline |

สถานะที่ตรวจ SIM-11: DRAFT, NEW, IN_PROGRESS, PENDING_CUSTOMER, PENDING_EXTERNAL, REOPENED, RESOLVED, CLOSED, CANCELLED, DUPLICATE

SIM-08 ถูกตัดออกจากขอบเขตตามเอกสาร จึงไม่เพิ่ม semantic/vector search

## ผลทดสอบจริง

- Backend ทั้งชุด: **121 ผ่าน / 3 ข้าม** — สามกรณีเป็น opt-in MariaDB และรันแยกแล้ว
- MariaDB จริง: **47 ผ่าน** สำหรับ SIM/WRK/CAT/registry/transaction timeout รวมการค้นหากับข้อมูลเพิ่ม 1,000 เคส
- Upgrade MariaDB จาก WRK ที่มีข้อมูลเดิม: **1 ผ่าน** — ข้อความเก่ายังอยู่, search_text และ FULLTEXT index พร้อม, มี migration head เดียว
- Playwright บน Microsoft Edge: **20 ผ่าน** รวม API จริง, desktop/mobile, canonical/legacy wire contract, CAT และ SIM timeout จำลอง
- `npm run lint`, `npm run typecheck`, `npm run build`: ผ่าน
- `npm audit --omit=dev`: ผ่าน ไม่พบช่องโหว่ใน production dependencies ณ วันที่ตรวจ
- Ruff สำหรับไฟล์ Python ใหม่และส่วน SIM ที่ปรับ: ผ่าน

แต่ละกลุ่มมีกรณีซ้ำบนคนละฐานข้อมูล ไม่ใช่ unique tests ที่นำมาบวกกัน

## ทดสอบซ้ำ

ติดตั้ง requirements-dev ของ Backend และใช้ `npm ci` ตาม lockfile ของ Frontend

```powershell
# ราก repository
python -m pytest backend/tests -q

# frontend: ใช้ Python ที่ติดตั้ง requirements-dev แล้ว
$env:WRK_QA_PYTHON = "path-to-python"
npm run test:sim-qa
npm run lint
npm run typecheck
npm run build

# backend: ตรวจและอัปเดต schema ของฐานที่ตั้งค่าไว้ตามขั้นตอนสำรองข้อมูลของโครงการ
python -m alembic heads
python -m alembic upgrade head
```

เกณฑ์คะแนนบังคับเลือกเริ่มต้น 60% ปรับผ่าน environment `SIM_DECISION_THRESHOLD`

การทดสอบ upgrade เปิดเฉพาะ `SIM_MIGRATION_QA=1` และตรวจ host/port/ชื่อฐานกับเงื่อนไขฐานว่าง เพื่อจำกัดไว้เฉพาะฐานชั่วคราว ห้ามเปิด flag นี้กับฐานใช้งานจริง

## ขอบเขตการเชื่อมต่อภายนอก

- Repository ยังไม่มีตัวส่ง LINE/อีเมลจริงหรือ customer identity ของ Portal การ QA WRK-03 รอบนี้ยืนยันการกรองข้อมูลและสิทธิ์ API ไม่ได้อ้างว่าทดสอบส่งข้อความถึงบัญชีภายนอกจริง
- Public Reply ของ WRK ล่าสุดใช้บันทึกการสื่อสารที่ผู้ใช้ส่งแล้วพร้อมช่องทางจริง การรวมครั้งนี้คงพฤติกรรมดังกล่าว
- KB/Known Issue จริงเป็น Phase 5 มี query hook เตรียมไว้ แต่ยังไม่เปิดแหล่งข้อมูลที่ไม่มีในระบบ
- REL ที่เชื่อมกับ SIM เป็น related-case link ไม่ครอบคลุม merge/master incident หรือปิดเคสกลุ่มของ REL ทั้งโมดูล
- การทดสอบ 1,000 เคสใช้ฐานชั่วคราว ไม่ใช่การทดสอบโหลดหรือข้อมูล production ของทีม
