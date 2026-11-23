"""Customer-originated cases (product SSO button and self-service portal).

Both entry points open cases through `open_case`, so they get the same intake
rules as staff capture: monthly case number, single-user severity, exam-window
priority, SLA clock, Tier 2 interval and private screenshot storage.
"""
import hashlib
from datetime import datetime, timezone
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.models.customer import ChannelIdentity, Contact, Organization
from app.db.models.master_data import Product
from app.db.models.portal import PortalIdentity, PortalSubmission
from app.db.models.ticket import Ticket
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.user import Role, User
from app.services import attachment_storage, sla_engine
from app.services.categorization import suggest_severity

IMAGES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024
IMAGE_ERROR = "รองรับภาพ PNG, JPEG หรือ WebP ขนาดไม่เกิน 10 MB"
CONTACT_ERROR = "กรุณาติดต่อทีมสนับสนุนเพื่อยืนยันข้อมูลผู้ติดต่อ"


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def intake_actor(db, preferred_id=None):
    """Account recorded as creator of customer-opened cases."""
    for user_id in (preferred_id, settings.PORTAL_INTAKE_USER_ID):
        if user_id:
            user = db.get(User, user_id)
            if user and user.is_active:
                return user
    if preferred_id is None and settings.PORTAL_INTAKE_USER_ID is None:
        admin = db.scalar(select(User).join(Role).where(Role.name == "Admin", User.is_active.is_(True))
                          .order_by(User.id).limit(1))
        if admin:
            return admin
    raise HTTPException(503, "ช่องทางแจ้งปัญหายังไม่พร้อม กรุณาติดต่อทีมสนับสนุน")


def resolve_product_identity(db, organization_id, issuer, subject, name, email):
    """Link a product account to one registry contact, creating it when new (POR-SSO-03)."""
    identity_key = hashlib.sha256(f"{issuer}:{subject}".encode()).hexdigest()
    link = db.get(PortalIdentity, (organization_id, identity_key))
    if link:
        contact = db.get(Contact, link.contact_id)
        if not contact or not contact.is_active or contact.organization_id != organization_id:
            raise HTTPException(403, CONTACT_ERROR)
        return contact
    email = str(email).lower()
    matches = db.scalars(select(Contact).join(ChannelIdentity).where(
        Contact.organization_id == organization_id,
        ChannelIdentity.channel_type == "email", func.lower(ChannelIdentity.value) == email,
    ).distinct()).all()
    if len(matches) > 1 or (matches and not matches[0].is_active):
        raise HTTPException(409, CONTACT_ERROR)
    contact = matches[0] if matches else Contact(organization_id=organization_id, name=name)
    if not matches:
        db.add(contact)
        db.flush()
        db.add(ChannelIdentity(contact_id=contact.id, channel_type="email", value=email))
    db.add(PortalIdentity(organization_id=organization_id, identity_key=identity_key, contact_id=contact.id))
    return contact


def existing_submission(db, grant_key):
    submission = db.get(PortalSubmission, grant_key) if grant_key else None
    return db.get(Ticket, submission.ticket_id) if submission else None


def check_screenshot(screenshot):
    if screenshot is not None and (screenshot.size or 0) > MAX_SCREENSHOT_BYTES:
        raise HTTPException(422, IMAGE_ERROR)


def open_case(db, *, actor, contact, instance, subject, description, user_agent, module_id=None,
              screenshot=None, source_url=None, exam_context=None, source="self_service", grant_key=None):
    """Create and commit a NEW portal case. Returns the ticket."""
    from app.api.v1.endpoints.tickets import next_ticket_number
    from app.services.routing import initialize_interval

    subject = (subject or "").strip()
    if not subject or len(subject) > 255 or len(description or "") > 20000:
        raise HTTPException(422, "กรุณาตรวจสอบหัวข้อ (ไม่เกิน 255 ตัวอักษร) และรายละเอียด")
    check_screenshot(screenshot)
    if (not instance or not instance.is_active or instance.organization_id != contact.organization_id):
        raise HTTPException(422, "กรุณาเลือกระบบที่ใช้งานอยู่ขององค์กรคุณ")
    product = db.get(Product, instance.product_id)
    if not product or not product.is_active:
        raise HTTPException(422, "ผลิตภัณฑ์นี้ปิดรับแจ้งปัญหาชั่วคราว")
    now = utcnow()
    source_url = urlsplit(source_url)._replace(query="", fragment="").geturl() if source_url else None
    ticket = Ticket(ticket_no=next_ticket_number(db, now), subject=subject, description=description or "",
                    status="NEW", channel="portal", organization_id=contact.organization_id,
                    contact_id=contact.id, product_instance_id=instance.id, module_id=module_id,
                    created_by_id=actor.id, current_tier=2, reported_at=now, created_at=now,
                    sla_policy_id=product.sla_policy_id or None, impact_scope="single_user",
                    severity=suggest_severity("single_user", False), source_url=source_url,
                    browser_device=(user_agent or "")[:255], exam_or_course_context=exam_context)
    written = []
    try:
        db.add(ticket)
        db.flush()
        history = TicketStatusHistory(ticket_id=ticket.id, from_status="NEW", to_status="NEW", created_at=now,
                                      details={"event": "CASE_CREATED", "source": source})
        db.add(history)
        db.flush()
        sla_engine.apply_exam_window(db, ticket, now)
        sla_engine.sync_clock(db, ticket, now)
        sla_engine.update_breach(db, ticket, now)
        initialize_interval(db, ticket, now, history.id)
        if grant_key:
            db.add(PortalSubmission(grant_key=grant_key, ticket_id=ticket.id))
        if screenshot is not None and screenshot.filename:
            suffix = PurePosixPath(screenshot.filename.lower()).suffix
            suffix = suffix if suffix in {".png", ".jpg", ".jpeg", ".webp"} else IMAGES.get(screenshot.content_type, "")
            _, written = attachment_storage.store_attachment(
                db, ticket.id, screenshot.file, "screenshot" + suffix, actor.id, allowed_types=set(IMAGES))
        db.commit()
    except Exception as exc:
        db.rollback()
        attachment_storage.discard(written)
        if isinstance(exc, IntegrityError):
            raise HTTPException(409, "บันทึกไม่สำเร็จ กรุณาลองใหม่อีกครั้ง") from None
        if isinstance(exc, HTTPException) and exc.status_code in (413, 415, 422):
            raise HTTPException(422, IMAGE_ERROR) from None
        raise
    return ticket


def lock_organization(db, organization_id):
    """Serialise concurrent intake for one customer (identity creation + numbering)."""
    db.scalar(select(Organization).where(Organization.id == organization_id).with_for_update())
