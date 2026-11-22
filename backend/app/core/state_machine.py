from app.core.labels import field_label, status_label
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from app.db.models.ticket import TicketStatus

REOPEN_WINDOW_DAYS = 14

TRANSITION_RULES: List[Dict[str, Any]] = [
    {
        "from": TicketStatus.DRAFT,
        "to": TicketStatus.NEW,
        "roles": ["User", "Customer", "Agent", "Admin"],
        "conditions": ["draft_required_fields"]
    },
    {
        "from": TicketStatus.NEW,
        "to": TicketStatus.IN_PROGRESS,
        "roles": ["Agent", "Admin"],
        "conditions": ["assignee_required"]
    },
    {
        "from": TicketStatus.IN_PROGRESS,
        "to": TicketStatus.PENDING_CUSTOMER,
        "roles": ["Agent", "Admin"],
        "conditions": []
    },
    {
        "from": TicketStatus.PENDING_CUSTOMER,
        "to": TicketStatus.IN_PROGRESS,
        "roles": ["Agent", "Customer", "Admin"],
        "conditions": []
    },
    {
        "from": TicketStatus.IN_PROGRESS,
        "to": TicketStatus.PENDING_EXTERNAL,
        "roles": ["Agent", "Admin"],
        "conditions": ["pending_external_reason_required"]
    },
    {
        "from": TicketStatus.PENDING_EXTERNAL,
        "to": TicketStatus.IN_PROGRESS,
        "roles": ["Agent", "Admin"],
        "conditions": []
    },
    {
        "from": TicketStatus.IN_PROGRESS,
        "to": TicketStatus.RESOLVED,
        "roles": ["Agent", "Admin"],
        "conditions": ["resolution_fields_required"]
    },
    {
        "from": TicketStatus.RESOLVED,
        "to": TicketStatus.CLOSED,
        "roles": ["Customer", "Admin", "System"],
        "conditions": []
    },
    {
        "from": TicketStatus.RESOLVED,
        "to": TicketStatus.REOPENED,
        "roles": ["Customer", "Agent", "Admin"],
        "conditions": ["reopen_reason_required"]
    },
    {
        "from": TicketStatus.CLOSED,
        "to": TicketStatus.REOPENED,
        "roles": ["Customer", "Agent", "Admin"],
        "conditions": ["reopen_reason_required"]
    },
    {
        "from": TicketStatus.REOPENED,
        "to": TicketStatus.IN_PROGRESS,
        "roles": ["Agent", "Admin"],
        "conditions": []
    },
]


def validate_status_transition(
    current_status: str,
    target_status: str,
    user_role: str,
    ticket_data: Optional[Dict[str, Any]] = None
) -> bool:
    if current_status not in TicketStatus._value2member_map_ or target_status not in TicketStatus._value2member_map_:
        raise HTTPException(422, 'ไม่รู้จักสถานะนี้')
    if target_status in (TicketStatus.DUPLICATE, TicketStatus.CANCELLED) and user_role not in {'Admin', 'Agent', 'User', 'Customer'}:
        raise HTTPException(403, 'บัญชีนี้ไม่มีสิทธิ์ยกเลิกเคสหรือทำเครื่องหมายว่าซ้ำ')
    if current_status == target_status:
        return True

    ticket_data = ticket_data or {}

    if target_status == TicketStatus.DUPLICATE:
        if not ticket_data.get("master_ticket_id"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="กรุณาเลือกเคสหลักก่อนทำเครื่องหมายว่าเคสซ้ำ"
            )
        return True

    if target_status == TicketStatus.CANCELLED:
        if not (ticket_data.get("cancel_reason") or "").strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="กรุณาระบุเหตุผลการยกเลิกเคส"
            )
        return True

    matched_rule = next(
        (
            rule for rule in TRANSITION_RULES 
            if rule["from"] == current_status and rule["to"] == target_status
        ),
        None
    )

    if not matched_rule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"เปลี่ยนสถานะจาก \"{status_label(current_status)}\" เป็น \"{status_label(target_status)}\" ไม่ได้"
        )

    if user_role not in matched_rule["roles"] and user_role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"บัญชีนี้ไม่มีสิทธิ์เปลี่ยนสถานะจาก \"{status_label(current_status)}\" เป็น \"{status_label(target_status)}\""
        )

    conditions = matched_rule["conditions"]

    if "draft_required_fields" in conditions:
        missing = [f for f in ["contact_id", "subject", "channel"] if not str(ticket_data.get(f) or "").strip()]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"กรุณากรอกให้ครบ: {', '.join(field_label(name) for name in missing)}"
            )

    if "assignee_required" in conditions and not ticket_data.get("assignee_id"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="กรุณาเลือกผู้ดำเนินการก่อนเริ่มดำเนินการ"
        )

    if "pending_external_reason_required" in conditions and not ticket_data.get("pending_external_reason"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="กรุณาระบุว่ากำลังรออะไรจากทีมพัฒนา/หน่วยงานภายนอก"
        )

    if "resolution_fields_required" in conditions:
        required_fields = ["category_id", "root_cause_code_id", "resolution_code_id", "product_instance_id", "resolution_detail"]
        missing = [f for f in required_fields if not str(ticket_data.get(f) or "").strip()]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"ก่อนแก้ไขเสร็จ กรุณากรอกให้ครบ: {', '.join(field_label(name) for name in missing)}"
            )

    if "reopen_reason_required" in conditions:
        if not ticket_data.get("reopen_reason"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="กรุณาระบุเหตุผลการเปิดเคสใหม่"
            )
        
        # ตรวจสอบกรอบเวลา 14 วันนับจาก closed_at หรือ resolved_at
        resolved_or_closed_at = ticket_data.get("closed_at") or ticket_data.get("resolved_at")
        if resolved_or_closed_at:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if isinstance(resolved_or_closed_at, datetime):
                ref_time = resolved_or_closed_at.replace(tzinfo=None)
            else:
                ref_time = resolved_or_closed_at
                time_diff = now - ref_time
                days_elapsed = time_diff.total_seconds() / 86400

            days_elapsed = (now - ref_time).days
            if now - ref_time > timedelta(days=REOPEN_WINDOW_DAYS):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"เคสปิดเกิน {REOPEN_WINDOW_DAYS} วันแล้ว เปิดใหม่ไม่ได้ กรุณาสร้างเคสต่อเนื่องแทน"
                )

    return True
