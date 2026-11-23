"""SEA-01 acceptance: Thai text without spaces is found with the team's usual words.

Subjects and terms come from real case examples in the SRS (section 2.3, 13.1)
and the wireframes. The PRD asks for at least 20 terms."""
from test_tickets import capture  # noqa: F401

CASES = [
    "ดาวน์โหลดข้อสอบไม่ได้ทั้งห้องสอบศูนย์สอบTU",
    "นักศึกษาส่งคำตอบไม่สำเร็จหลังกดยืนยัน",
    "อาจารย์เข้าระบบไม่ได้หลังเปลี่ยนรหัสผ่าน",
    "ขอเพิ่มสิทธิ์อาจารย์เข้ากลุ่มรายวิชา",
    "คะแนนสอบแสดงผลผิดในรายงานผู้สอบ",
    "ขอส่งออกข้อสอบทั้งคลังเป็นไฟล์เวิร์ด",
    "แอปค้างระหว่างสอบบนแท็บเล็ต",
    "ตั้งเวลาสอบผิดทำให้หมดเวลาก่อนกำหนด",
    "บันทึกหัตถการไม่สำเร็จในสมุดบันทึก",
    "อาจารย์รับรองผลไม่ได้เพราะไม่ได้รับการแจ้งเตือน",
]
TERMS = [
    ("ดาวน์โหลด", 0), ("ข้อสอบ", 0), ("ห้องสอบ", 0), ("ศูนย์สอบ", 0),
    ("ส่งคำตอบ", 1), ("ไม่สำเร็จ", 1), ("เข้าระบบ", 2), ("รหัสผ่าน", 2),
    ("สิทธิ์", 3), ("รายวิชา", 3), ("คะแนน", 4), ("รายงาน", 4),
    ("ส่งออก", 5), ("คลัง", 5), ("ค้าง", 6), ("แท็บเล็ต", 6),
    ("หมดเวลา", 7), ("ตั้งเวลา", 7), ("หัตถการ", 8), ("แจ้งเตือน", 9),
]


def test_twenty_thai_terms_find_the_right_case(capture):
    client, _, _, data, _ = capture
    numbers = []
    for subject in CASES:
        body = dict(data, subject=subject, channel="phone")
        similar = client.get("/api/v1/tickets/similar", params={
            "q": subject, "organization_id": data["organization_id"],
            "product_instance_id": data["product_instance_id"]}).json()
        if similar.get("decision_required"):
            client.post(f"/api/v1/tickets/similarity-feedback/{similar['feedback_id']}", json={"decision": "new"})
            body["similarity_feedback_id"] = similar["feedback_id"]
        created = client.post("/api/v1/tickets", json=body)
        assert created.status_code == 201, created.text
        numbers.append(created.json()["ticket_no"])
    assert len(TERMS) >= 20
    misses = []
    for term, expected in TERMS:
        result = client.post("/api/v1/case-search/query", json={"q": term}).json()
        found = {item["ticket_no"] for item in result["items"]}
        if numbers[expected] not in found:
            misses.append(term)
    assert not misses, f"Thai search missed: {misses}"
