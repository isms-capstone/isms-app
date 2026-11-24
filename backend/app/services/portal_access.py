"""Customer sessions for the self-service portal (POR-07..09).

A portal session is a short-lived HS256 token of type "portal" that names one
active registry contact. It is never accepted by staff endpoints (those require
type "access"), and staff tokens are never accepted here. Sessions start from a
product grant (SSO button) or a one-time e-mail link (POR-09).
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import JWTError, jwt
from sqlalchemy import func, or_, select

from app.core.config import settings
from app.db.models.customer import ChannelIdentity, Contact, Organization
from app.db.models.portal import PortalMagicLink, PortalOutbox
from app.db.models.ticket import Ticket

SESSION_TYPE = "portal"
LINK_MINUTES = 15
LINK_RESEND_SECONDS = 60
EXPIRED = "เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่"


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def issue_session(contact):
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.PORTAL_SESSION_HOURS)
    return jwt.encode({"type": SESSION_TYPE, "sub": str(contact.id), "org": contact.organization_id,
                       "exp": expires}, settings.SECRET_KEY, algorithm="HS256")


def session_response(contact):
    return {"session": issue_session(contact), "max_age": settings.PORTAL_SESSION_HOURS * 3600,
            "name": contact.name}


def contact_from_session(db, token):
    try:
        claims = jwt.decode(token or "", settings.SECRET_KEY, algorithms=["HS256"],
                            options={"require_exp": True})
        if claims.get("type") != SESSION_TYPE:
            raise JWTError("wrong token type")
        contact = db.get(Contact, int(claims["sub"]))
    except (JWTError, KeyError, TypeError, ValueError):
        raise HTTPException(401, EXPIRED) from None
    organization = db.get(Organization, contact.organization_id) if contact else None
    if (not contact or not contact.is_active or contact.organization_id != claims.get("org")
            or not organization or not organization.is_active):
        raise HTTPException(401, EXPIRED)
    return contact


def visible_cases(contact):
    """POR-08: a coordinator sees every case of the organisation, others only their own."""
    query = select(Ticket).where(Ticket.organization_id == contact.organization_id,
                                 Ticket.status.not_in(("DRAFT", "CANCELLED")))
    if contact.portal_scope != "organization":
        query = query.where(Ticket.contact_id == contact.id)
    return query


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def request_magic_links(db, email, now=None):
    """Queue one sign-in e-mail per active contact with this address.

    Returns the raw links (for local development only). Callers must answer the
    same way whether or not the address exists, to avoid revealing customers."""
    now = now or utcnow()
    email = email.strip().lower()
    contacts = db.scalars(select(Contact).join(ChannelIdentity).join(Organization).where(
        ChannelIdentity.channel_type == "email", func.lower(ChannelIdentity.value) == email,
        Contact.is_active.is_(True), Organization.is_active.is_(True)).distinct()).all()
    links = []
    for contact in contacts:
        recent = db.scalar(select(PortalMagicLink.token_hash).where(
            PortalMagicLink.contact_id == contact.id,
            PortalMagicLink.created_at > now - timedelta(seconds=LINK_RESEND_SECONDS)).limit(1))
        if recent:
            continue  # throttle repeated requests
        token = secrets.token_urlsafe(32)
        db.add(PortalMagicLink(token_hash=_hash(token), contact_id=contact.id, email=email,
                               created_at=now, expires_at=now + timedelta(minutes=LINK_MINUTES)))
        url = f"{settings.PORTAL_BASE_URL.rstrip('/')}/portal/login?token={token}"
        organization = db.get(Organization, contact.organization_id)
        db.add(PortalOutbox(recipient=email, created_at=now,
                            subject="ลิงก์เข้าสู่ระบบติดตามเคส ISMS",
                            body=(f"เรียน {contact.name}\n\n"
                                  f"กดลิงก์นี้เพื่อดูเคสของ {organization.name} (ใช้ได้ครั้งเดียว ภายใน {LINK_MINUTES} นาที)\n"
                                  f"{url}\n\nหากคุณไม่ได้ขอลิงก์นี้ ไม่ต้องดำเนินการใด ๆ")))
        links.append(url)
    db.commit()
    return links


def redeem_magic_link(db, token, now=None):
    now = now or utcnow()
    row = db.scalar(select(PortalMagicLink).where(PortalMagicLink.token_hash == _hash(token or ""))
                    .with_for_update())
    if not row or row.used_at is not None or row.expires_at <= now:
        raise HTTPException(401, "ลิงก์หมดอายุหรือถูกใช้ไปแล้ว กรุณาขอลิงก์ใหม่")
    contact = db.get(Contact, row.contact_id)
    if not contact or not contact.is_active:
        raise HTTPException(401, "ลิงก์หมดอายุหรือถูกใช้ไปแล้ว กรุณาขอลิงก์ใหม่")
    row.used_at = now
    db.commit()
    return contact


def purge_expired_links(db, now=None):
    now = now or utcnow()
    db.query(PortalMagicLink).filter(or_(PortalMagicLink.expires_at < now - timedelta(days=1),
                                         PortalMagicLink.used_at < now - timedelta(days=1))
                                     ).delete(synchronize_session=False)
    db.commit()
