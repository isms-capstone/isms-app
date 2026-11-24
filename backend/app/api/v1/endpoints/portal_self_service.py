"""Self-service portal for customer contacts (POR-07..10).

Customer routes read the session from the X-Portal-Session header, which the
Next.js server copies from an HttpOnly cookie; browsers never see the token.
Staff routes (announcements, contact visibility) use the normal staff login.
"""
import os
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import RoleChecker
from app.core.config import settings
from app.core.labels import status_label
from app.db.models.customer import Contact, Organization
from app.db.models.master_data import Product
from app.db.models.portal import PortalAnnouncement
from app.db.models.product import ProductInstance
from app.db.models.ticket import OPEN_STATUSES, Ticket
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.work_category import TicketWorklog
from app.db.session import get_db
from app.services import portal_access, portal_intake
from app.services.external_communication import external_replies

router = APIRouter(prefix="/portal", tags=["Self-service portal"])
announcement_editor = RoleChecker(["Admin", "Team Lead"])
contact_editor = RoleChecker(["Admin", "Team Lead", "Agent"])


def current_contact(x_portal_session: str = Header(""), db: Session = Depends(get_db)) -> Contact:
    return portal_access.contact_from_session(db, x_portal_session)


def iso(value: datetime | None):
    return value.isoformat() + "Z" if value else None


def product_names(db, instance_ids):
    rows = db.execute(select(ProductInstance.id, ProductInstance.name, Product.name)
                      .join(Product, Product.id == ProductInstance.product_id)
                      .where(ProductInstance.id.in_(instance_ids or [0]))).all()
    return {row[0]: {"product": row[2], "system": row[1]} for row in rows}


# ---------------------------------------------------------------- sign-in

class LinkRequest(BaseModel):
    email: EmailStr


class LinkRedeem(BaseModel):
    token: str = Field(min_length=20, max_length=200)


@router.post("/magic-link", status_code=202)
def request_link(body: LinkRequest, db: Session = Depends(get_db)):
    links = portal_access.request_magic_links(db, str(body.email))
    response = {"message": "หากอีเมลนี้อยู่ในระบบ เราได้ส่งลิงก์เข้าสู่ระบบไปแล้ว ลิงก์ใช้ได้ 15 นาที"}
    # Local development without SMTP: show the link so the flow can be tried end to end.
    if settings.is_local and not os.getenv("POR_SMTP_HOST"):
        response["dev_links"] = links
    return response


@router.post("/magic-link/verify")
def redeem_link(body: LinkRedeem, db: Session = Depends(get_db)):
    return portal_access.session_response(portal_access.redeem_magic_link(db, body.token))


# ---------------------------------------------------------------- customer

@router.get("/me")
def me(contact: Contact = Depends(current_contact), db: Session = Depends(get_db)):
    organization = db.get(Organization, contact.organization_id)
    systems = db.execute(select(ProductInstance.id, ProductInstance.name, Product.name)
                         .join(Product, Product.id == ProductInstance.product_id)
                         .where(ProductInstance.organization_id == contact.organization_id,
                                ProductInstance.is_active.is_(True), Product.is_active.is_(True))
                         .order_by(Product.name, ProductInstance.name)).all()
    return {"name": contact.name, "organization": organization.name, "scope": contact.portal_scope,
            "systems": [{"id": row[0], "name": row[1], "product": row[2]} for row in systems]}


@router.get("/me/cases")
def my_cases(status: Literal["open", "closed", "all"] = "all", contact: Contact = Depends(current_contact),
             db: Session = Depends(get_db)):
    query = portal_access.visible_cases(contact)
    if status == "open":
        query = query.where(Ticket.status.in_(OPEN_STATUSES))
    elif status == "closed":
        query = query.where(Ticket.status.not_in(OPEN_STATUSES))
    rows = db.scalars(query.order_by(Ticket.created_at.desc(), Ticket.id.desc()).limit(200)).all()
    names = product_names(db, {row.product_instance_id for row in rows if row.product_instance_id})
    reporters = {row.id: row.name for row in db.scalars(
        select(Contact).where(Contact.id.in_({row.contact_id for row in rows if row.contact_id} or {0})))}
    reply_counts = dict(db.execute(
        select(TicketWorklog.ticket_id, func.count()).where(
            TicketWorklog.ticket_id.in_([row.id for row in rows] or [0]),
            TicketWorklog.is_internal.is_(False), TicketWorklog.channel == "portal")
        .group_by(TicketWorklog.ticket_id)).all())
    return [{"ticket_no": row.ticket_no, "subject": row.subject, "status": row.status,
             "status_label": status_label(row.status), "created_at": iso(row.created_at),
             "product": names.get(row.product_instance_id, {}).get("product"),
             "reporter": reporters.get(row.contact_id), "replies": reply_counts.get(row.id, 0)}
            for row in rows]


@router.get("/me/cases/{ticket_no}")
def my_case(ticket_no: str, contact: Contact = Depends(current_contact), db: Session = Depends(get_db)):
    ticket = db.scalar(portal_access.visible_cases(contact).where(Ticket.ticket_no == ticket_no))
    if not ticket:
        raise HTTPException(404, "ไม่พบเคสนี้ หรือคุณไม่มีสิทธิ์ดู")
    history = db.scalars(select(TicketStatusHistory).where(
        TicketStatusHistory.ticket_id == ticket.id,
        TicketStatusHistory.from_status != TicketStatusHistory.to_status)
        .order_by(TicketStatusHistory.created_at, TicketStatusHistory.id)).all()
    names = product_names(db, [ticket.product_instance_id])
    reporter = db.get(Contact, ticket.contact_id) if ticket.contact_id else None
    return {
        "ticket_no": ticket.ticket_no, "subject": ticket.subject, "description": ticket.description,
        "status": ticket.status, "status_label": status_label(ticket.status),
        "created_at": iso(ticket.created_at), "resolved_at": iso(ticket.resolved_at),
        "product": names.get(ticket.product_instance_id, {}).get("product"),
        "system": names.get(ticket.product_instance_id, {}).get("system"),
        "reporter": reporter.name if reporter else None,
        # WRK-03: only public replies delivered through the portal; internal notes never leave the team.
        "replies": external_replies(db, ticket.id, "portal"),
        "history": [{"status": row.to_status, "status_label": status_label(row.to_status),
                     "at": iso(row.created_at)} for row in history],
    }


@router.post("/me/cases", status_code=201)
def open_my_case(request: Request, subject: str = Form(...), description: str = Form(""),
                 product_instance_id: int = Form(...), screenshot: UploadFile | None = File(None),
                 contact: Contact = Depends(current_contact), db: Session = Depends(get_db)):
    portal_intake.lock_organization(db, contact.organization_id)
    ticket = portal_intake.open_case(
        db, actor=portal_intake.intake_actor(db), contact=contact,
        instance=db.get(ProductInstance, product_instance_id), subject=subject, description=description,
        screenshot=screenshot, user_agent=request.headers.get("user-agent"), source="self_service")
    return {"ticket_no": ticket.ticket_no}


# ---------------------------------------------------------------- status notices (POR-10)

class AnnouncementInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=5000)
    ticket_no: str | None = Field(None, max_length=32)
    product_id: int | None = Field(None, ge=1)

    @field_validator("title", "message", mode="before")
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value


def announcement_json(db, row, staff=False):
    ticket = db.get(Ticket, row.ticket_id) if row.ticket_id else None
    product = db.get(Product, row.product_id) if row.product_id else None
    data = {"id": row.id, "title": row.title, "message": row.message, "is_active": row.is_active,
            "product": product.name if product else None, "created_at": iso(row.created_at),
            "resolved_at": iso(row.resolved_at),
            "status_label": status_label(ticket.status) if ticket else None}
    if staff:
        data["ticket_no"] = ticket.ticket_no if ticket else None
    return data


@router.get("/announcements")
def public_announcements(db: Session = Depends(get_db)):
    """Public: incidents that are happening now. Notices tied to a master
    incident disappear automatically once that case is resolved or closed."""
    rows = db.scalars(select(PortalAnnouncement).where(PortalAnnouncement.is_active.is_(True))
                      .order_by(PortalAnnouncement.created_at.desc()).limit(20)).all()
    visible = []
    for row in rows:
        ticket = db.get(Ticket, row.ticket_id) if row.ticket_id else None
        if ticket and ticket.status not in OPEN_STATUSES:
            continue
        visible.append(announcement_json(db, row))
    return visible


@router.get("/announcements/manage")
def manage_announcements(db: Session = Depends(get_db), user=Depends(announcement_editor)):
    rows = db.scalars(select(PortalAnnouncement).order_by(PortalAnnouncement.created_at.desc()).limit(50)).all()
    return [announcement_json(db, row, staff=True) for row in rows]


@router.post("/announcements", status_code=201)
def create_announcement(body: AnnouncementInput, db: Session = Depends(get_db), user=Depends(announcement_editor)):
    ticket_id = None
    if body.ticket_no:
        ticket = db.scalar(select(Ticket).where(Ticket.ticket_no == body.ticket_no.strip().upper()))
        if not ticket or ticket.status in ("DRAFT", "CANCELLED", "DUPLICATE"):
            raise HTTPException(422, "ไม่พบเคสหลักตามเลขที่ระบุ")
        ticket_id = ticket.id
    if body.product_id and not db.get(Product, body.product_id):
        raise HTTPException(422, "ไม่พบผลิตภัณฑ์")
    row = PortalAnnouncement(title=body.title, message=body.message, ticket_id=ticket_id,
                             product_id=body.product_id, is_active=True, created_by_id=user.id,
                             created_at=portal_access.utcnow())
    db.add(row)
    db.commit()
    return announcement_json(db, row, staff=True)


@router.post("/announcements/{announcement_id}/resolve")
def resolve_announcement(announcement_id: int, db: Session = Depends(get_db), user=Depends(announcement_editor)):
    row = db.get(PortalAnnouncement, announcement_id)
    if not row:
        raise HTTPException(404, "ไม่พบประกาศนี้")
    row.is_active = False
    row.resolved_at = row.resolved_at or portal_access.utcnow()
    db.commit()
    return announcement_json(db, row, staff=True)


# ---------------------------------------------------------------- contact visibility (POR-08)

class ScopeInput(BaseModel):
    scope: Literal["own", "organization"]


@router.put("/contacts/{contact_id}/scope")
def set_contact_scope(contact_id: int, body: ScopeInput, db: Session = Depends(get_db),
                      user=Depends(contact_editor)):
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(404, "ไม่พบผู้ติดต่อ")
    contact.portal_scope = body.scope
    db.commit()
    return {"id": contact.id, "scope": contact.portal_scope}

