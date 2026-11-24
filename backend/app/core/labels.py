"""Thai names for fields and records that appear inside user-facing errors."""

FIELD_LABELS = {
    "assignee_id": "ผู้ดำเนินการ",
    "owner_id": "เจ้าของเคส",
    "root_cause_code_id": "รหัสสาเหตุ",
    "resolution_code_id": "รหัสวิธีแก้",
    "resolution_detail": "รายละเอียดวิธีแก้",
    "category_id": "ประเภทปัญหา",
    "problem_type_id": "ประเภทปัญหา",
    "product_instance_id": "ระบบของลูกค้า",
    "module_id": "โมดูล",
    "symptom_id": "อาการ",
    "service_stage_id": "ช่วงเวลาของการสอบ",
    "ticket_type_id": "ประเภทเคส",
    "department_id": "หน่วยงาน",
    "course_or_exam_id": "รายวิชา/การสอบ",
    "organization_id": "ลูกค้า",
    "contact_id": "ผู้แจ้ง",
    "subject": "หัวข้อ",
    "channel": "ช่องทาง",
}
MODEL_LABELS = {
    "Contact": "ผู้แจ้ง",
    "Organization": "ลูกค้า",
    "Department": "หน่วยงาน",
    "CourseOrExam": "รายวิชา/การสอบ",
    "ProductInstance": "ระบบของลูกค้า",
    "TicketType": "ประเภทเคส",
    "Product": "ผลิตภัณฑ์",
    "Team": "ทีม",
    "User": "ผู้ใช้",
    "Ticket": "เคส",
}
STATUS_LABELS = {
    "DRAFT": "ร่าง", "NEW": "ใหม่", "IN_PROGRESS": "กำลังดำเนินการ", "PENDING_CUSTOMER": "รอลูกค้า",
    "PENDING_EXTERNAL": "รอทีมพัฒนา/ภายนอก", "RESOLVED": "แก้ไขแล้ว", "CLOSED": "ปิดแล้ว",
    "REOPENED": "เปิดใหม่", "DUPLICATE": "ซ้ำ", "CANCELLED": "ยกเลิก",
}


def field_label(name: str) -> str:
    return FIELD_LABELS.get(name, name)


def model_label(name: str) -> str:
    return MODEL_LABELS.get(name, name)


def status_label(value) -> str:
    value = getattr(value, "value", value)
    return STATUS_LABELS.get(str(value), str(value))
