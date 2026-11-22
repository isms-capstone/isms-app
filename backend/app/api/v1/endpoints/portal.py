"""Product SSO intake. Product grants are separate from staff authentication."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.v1.endpoints import tickets
from app.db.models.customer import ChannelIdentity, Contact, Organization
from app.db.models.product import Product, ProductInstance, ProductModule
from app.db.models.portal import PortalIdentity, PortalSubmission
from app.services.external_communication import external_replies
from app.db.models.ticket import Ticket
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.user import User
from app.db.session import get_db
from app.services import attachment_storage, sla_engine
from app.services.categorization import suggest_severity

router = APIRouter(prefix="/portal", tags=["Product SSO"])
AUDIENCE = "isms-portal"
IMAGES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024


class Grant(BaseModel):
    iss: str = Field(min_length=1, max_length=50)
    sub: str = Field(min_length=1, max_length=255)
    jti: str = Field(min_length=16, max_length=128)
    iat: int = Field(strict=True)
    exp: int = Field(strict=True)
    organization_id: int = Field(gt=0)
    instance_id: int = Field(gt=0)
    module_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    source_url: str = Field(max_length=2048)
    exam_or_course_context: str | None = Field(default=None, max_length=255)


def verified(token, db):
    denied = HTTPException(401, "ลิงก์แจ้งปัญหาใช้ไม่ได้ กรุณาเปิดใหม่จากผลิตภัณฑ์")
    if len(token) > 3800:
        raise denied
    try:
        issuer = jwt.get_unverified_claims(token).get("iss")
        if not isinstance(issuer, str):
            raise denied
        config = json.loads(os.getenv("POR_PRODUCTS") or "{}").get(issuer)
        if not config or len(config["secret"].encode()) < 32:
            raise denied
        claims = Grant.model_validate(jwt.decode(
            token, config["secret"], algorithms=["HS256"], audience=AUDIENCE,
            issuer=issuer, options={"require_aud": True, "require_exp": True, "require_iat": True},
        ))
        now = int(datetime.now(timezone.utc).timestamp())
        if not claims.iat <= now < claims.exp <= claims.iat + 300:
            raise denied
        url = urlsplit(claims.source_url)
        if (url.scheme != "https" or url.username or url.password or
                f"{url.scheme}://{url.netloc}" not in config["origins"]):
            raise denied
    except (JWTError, ValidationError, ValueError, KeyError, TypeError, AttributeError):
        raise denied from None
    instance = db.get(ProductInstance, claims.instance_id)
    module = db.get(ProductModule, claims.module_id)
    org = db.get(Organization, claims.organization_id)
    product = db.get(Product, instance.product_id) if instance else None
    if (not product or not product.is_active or not instance or not instance.is_active or instance.organization_id != claims.organization_id
            or instance.product_id != config["product_id"]
            or not module or not module.is_active or module.product_id != instance.product_id
            or not org or not org.is_active):
        raise denied
    return claims, config


@router.post("/sso-entry")
def entry(token: str = Form(...), db=Depends(get_db)):
    claims, _ = verified(token, db)
    return {"product": claims.iss, "name": claims.name, "context": claims.exam_or_course_context}


@router.post("/cases", status_code=201)
def create_case(request: Request, token: str = Form(...), subject: str = Form(...),
                description: str = Form(""), screenshot: UploadFile | None = File(None),
                db=Depends(get_db)):
    claims, config = verified(token, db)
    subject = subject.strip()
    if not subject or len(subject) > 255 or len(description) > 20000:
        raise HTTPException(422, "กรุณาตรวจสอบหัวข้อและรายละเอียด")
    actor = db.get(User, config["intake_user_id"])
    if not actor or not actor.is_active:
        raise HTTPException(503, "ช่องทางแจ้งปัญหายังไม่พร้อม")
    if screenshot is not None and (screenshot.size or 0) > MAX_SCREENSHOT_BYTES:
        raise HTTPException(422, "รองรับภาพ PNG, JPEG หรือ WebP ขนาดไม่เกิน 10 MB")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    grant_key = hashlib.sha256(json.dumps([claims.iss, claims.sub, claims.organization_id,
                                           claims.instance_id, claims.jti]).encode()).hexdigest()
    identity_key = hashlib.sha256(f"{claims.iss}:{claims.sub}".encode()).hexdigest()
    from app.services.routing import initialize_interval

    db.scalar(select(Organization).where(Organization.id == claims.organization_id).with_for_update())
    submission = db.get(PortalSubmission, grant_key)
    if submission:
        existing = db.get(Ticket, submission.ticket_id)
        return {"ticket_no": existing.ticket_no}
    link = db.get(PortalIdentity, (claims.organization_id, identity_key))
    if link:
        contact = db.get(Contact, link.contact_id)
        if not contact or not contact.is_active or contact.organization_id != claims.organization_id:
            raise HTTPException(403, "กรุณาติดต่อทีมสนับสนุนเพื่อยืนยันข้อมูลผู้ติดต่อ")
    else:
        email = str(claims.email).lower()
        matches = db.scalars(select(Contact).join(ChannelIdentity).where(
            Contact.organization_id == claims.organization_id,
            ChannelIdentity.channel_type == "email", func.lower(ChannelIdentity.value) == email,
        ).distinct()).all()
        if len(matches) > 1 or (matches and not matches[0].is_active):
            raise HTTPException(409, "กรุณาติดต่อทีมสนับสนุนเพื่อยืนยันข้อมูลผู้ติดต่อ")
        contact = matches[0] if matches else Contact(organization_id=claims.organization_id, name=claims.name)
        if not matches:
            db.add(contact)
            db.flush()
            db.add(ChannelIdentity(contact_id=contact.id, channel_type="email", value=email))
        db.add(PortalIdentity(organization_id=claims.organization_id, identity_key=identity_key, contact_id=contact.id))
    instance = db.get(ProductInstance, claims.instance_id)
    product = db.get(Product, instance.product_id)
    source = urlsplit(claims.source_url)
    ticket = Ticket(ticket_no=tickets.next_ticket_number(db, now), subject=subject, description=description,
                    status="NEW", channel="portal", organization_id=claims.organization_id,
                    contact_id=contact.id, product_instance_id=claims.instance_id, module_id=claims.module_id,
                    created_by_id=actor.id, current_tier=2, reported_at=now, created_at=now,
                    sla_policy_id=product.sla_policy_id if product.sla_policy_id else None,
                    impact_scope="single_user", severity=suggest_severity("single_user", False),
                    source_url=source._replace(query="", fragment="").geturl(),
                    browser_device=request.headers.get("user-agent", "")[:255],
                    exam_or_course_context=claims.exam_or_course_context)
    written = []
    try:
        db.add(ticket)
        db.flush()
        history = TicketStatusHistory(ticket_id=ticket.id, from_status="NEW", to_status="NEW",
                                      created_at=now, details={"event": "CASE_CREATED", "source": "product_sso"})
        db.add(history)
        db.flush()
        # Same intake rules as staff capture: exam-window priority, SLA clock, tier interval.
        sla_engine.apply_exam_window(db, ticket, now)
        sla_engine.sync_clock(db, ticket, now)
        initialize_interval(db, ticket, now, history.id)
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
            raise HTTPException(409, "บันทึกไม่สำเร็จ กรุณาเปิดฟอร์มใหม่จากผลิตภัณฑ์") from None
        if isinstance(exc, HTTPException) and exc.status_code in (413, 415, 422):
            raise HTTPException(422, "รองรับภาพ PNG, JPEG หรือ WebP ขนาดไม่เกิน 10 MB") from None
        raise
    return {"ticket_no": ticket.ticket_no}


@router.post("/status")
def case_status(token: str = Form(...), db=Depends(get_db)):
    claims, _ = verified(token, db)
    identity = hashlib.sha256(f"{claims.iss}:{claims.sub}".encode()).hexdigest()
    link = db.get(PortalIdentity, (claims.organization_id, identity))
    contact = db.get(Contact, link.contact_id) if link else None
    if not contact or not contact.is_active or contact.organization_id != claims.organization_id:
        return []
    rows = db.scalars(select(Ticket).where(
        Ticket.contact_id == contact.id, Ticket.organization_id == claims.organization_id,
        Ticket.product_instance_id == claims.instance_id, Ticket.channel == "portal",
        Ticket.status != "DRAFT",
    ).order_by(Ticket.id.desc()).limit(50)).all()
    return [{"ticket_no": row.ticket_no, "subject": row.subject, "status": row.status,
             "replies": external_replies(db, row.id, "portal")} for row in rows]
