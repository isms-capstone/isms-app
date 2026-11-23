"""Product SSO intake. Product grants are separate from staff authentication."""
import hashlib
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field, ValidationError
from sqlalchemy import select

from app.db.models.customer import Contact, Organization
from app.db.models.product import Product, ProductInstance, ProductModule
from app.db.models.portal import PortalIdentity
from app.services.external_communication import external_replies
from app.db.models.ticket import Ticket
from app.db.session import get_db
from app.services import portal_access, portal_intake

router = APIRouter(prefix="/portal", tags=["Product SSO"])
AUDIENCE = "isms-portal"


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
    actor = portal_intake.intake_actor(db, config["intake_user_id"])
    portal_intake.check_screenshot(screenshot)
    grant_key = hashlib.sha256(json.dumps([claims.iss, claims.sub, claims.organization_id,
                                           claims.instance_id, claims.jti]).encode()).hexdigest()
    portal_intake.lock_organization(db, claims.organization_id)
    existing = portal_intake.existing_submission(db, grant_key)
    if existing:  # retrying the same grant returns the case it already created
        return {"ticket_no": existing.ticket_no}
    contact = portal_intake.resolve_product_identity(
        db, claims.organization_id, claims.iss, claims.sub, claims.name, claims.email)
    ticket = portal_intake.open_case(
        db, actor=actor, contact=contact, instance=db.get(ProductInstance, claims.instance_id),
        module_id=claims.module_id, subject=subject, description=description, screenshot=screenshot,
        user_agent=request.headers.get("user-agent"), source_url=claims.source_url,
        exam_context=claims.exam_or_course_context, source="product_sso", grant_key=grant_key)
    return {"ticket_no": ticket.ticket_no}


@router.post("/session")
def session_from_grant(token: str = Form(...), db=Depends(get_db)):
    """Exchange a product grant for a self-service portal session (POR-07 via SSO)."""
    claims, _ = verified(token, db)
    portal_intake.lock_organization(db, claims.organization_id)
    contact = portal_intake.resolve_product_identity(
        db, claims.organization_id, claims.iss, claims.sub, claims.name, claims.email)
    db.commit()
    return portal_access.session_response(contact)


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
