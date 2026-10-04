from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.models.customer import ChannelIdentity, Contact, Organization
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.customer import (
    ChannelCreate, ChannelResponse, ContactCreate, ContactResponse,
    OrganizationCreate, OrganizationResponse,
)


REGISTRY_EDITOR_ROLES = frozenset({"Admin", "User", "Agent", "Team Lead"})


def require_registry_editor(user: User = Depends(get_current_user)):
    # Match business role names, never generated database IDs. User is the
    # legacy INFRA role; keep compatibility until ADM introduces Agent roles.
    if not user.role or user.role.name not in REGISTRY_EDITOR_ROLES:
        raise HTTPException(403, "Customer registry is read-only for this role")
    return user


router = APIRouter(dependencies=[Depends(get_current_user)])


def get_record(db, model, record_id):
    record = db.get(model, record_id)
    if record is None:
        raise HTTPException(404, "Record not found")
    return record


def save(db, record):
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Channel already exists for this contact") from None
    db.refresh(record)
    return record


@router.get("/organizations", response_model=list[OrganizationResponse])
def organizations(q: str = Query("", max_length=255), offset: int = Query(0, ge=0),
                  limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    query = select(Organization)
    if q.strip():
        term = q.strip()
        matching_contacts = select(Contact.organization_id).where(or_(
            Contact.name.contains(term, autoescape=True),
            Contact.channels.any(ChannelIdentity.value.contains(term, autoescape=True)),
        ))
        query = query.where(or_(Organization.name.contains(term, autoescape=True),
                                Organization.id.in_(matching_contacts)))
    return db.scalars(query.order_by(Organization.name, Organization.id).offset(offset).limit(limit)).all()


@router.post("/organizations", response_model=OrganizationResponse, status_code=201,
             dependencies=[Depends(require_registry_editor)])
def create_organization(body: OrganizationCreate, db: Session = Depends(get_db)):
    return save(db, Organization(**body.model_dump()))


@router.get("/organizations/{organization_id}", response_model=OrganizationResponse)
def organization(organization_id: int, db: Session = Depends(get_db)):
    return get_record(db, Organization, organization_id)


@router.put("/organizations/{organization_id}", response_model=OrganizationResponse,
            dependencies=[Depends(require_registry_editor)])
def update_organization(organization_id: int, body: OrganizationCreate, db: Session = Depends(get_db)):
    record = get_record(db, Organization, organization_id)
    for key, value in body.model_dump().items():
        setattr(record, key, value)
    return save(db, record)


@router.get("/contacts", response_model=list[ContactResponse])
def contacts(q: str = Query("", max_length=255), organization_id: int | None = None,
             offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
             db: Session = Depends(get_db)):
    query = select(Contact).options(selectinload(Contact.channels))
    if organization_id is not None:
        get_record(db, Organization, organization_id)
        query = query.where(Contact.organization_id == organization_id)
    if q.strip():
        term = q.strip()
        query = query.where(or_(Contact.name.contains(term, autoescape=True),
                               Contact.channels.any(ChannelIdentity.value.contains(term, autoescape=True))))
    return db.scalars(query.order_by(Contact.name, Contact.id).offset(offset).limit(limit)).all()


@router.post("/organizations/{organization_id}/contacts", response_model=ContactResponse, status_code=201,
             dependencies=[Depends(require_registry_editor)])
def create_contact(organization_id: int, body: ContactCreate, db: Session = Depends(get_db)):
    get_record(db, Organization, organization_id)
    return save(db, Contact(organization_id=organization_id, **body.model_dump()))


@router.get("/contacts/{contact_id}", response_model=ContactResponse)
def contact(contact_id: int, db: Session = Depends(get_db)):
    return get_record(db, Contact, contact_id)


@router.put("/contacts/{contact_id}", response_model=ContactResponse,
            dependencies=[Depends(require_registry_editor)])
def update_contact(contact_id: int, body: ContactCreate, db: Session = Depends(get_db)):
    record = get_record(db, Contact, contact_id)
    for key, value in body.model_dump().items():
        setattr(record, key, value)
    return save(db, record)


@router.post("/contacts/{contact_id}/channels", response_model=ChannelResponse, status_code=201,
             dependencies=[Depends(require_registry_editor)])
def create_channel(contact_id: int, body: ChannelCreate, db: Session = Depends(get_db)):
    get_record(db, Contact, contact_id)
    values = body.model_dump()
    if body.channel_type == "email":
        values["value"] = body.value.casefold()
    return save(db, ChannelIdentity(contact_id=contact_id, **values))


@router.delete("/contacts/{contact_id}/channels/{channel_id}", status_code=204,
               dependencies=[Depends(require_registry_editor)])
def delete_channel(contact_id: int, channel_id: int, db: Session = Depends(get_db)):
    record = get_record(db, ChannelIdentity, channel_id)
    if record.contact_id != contact_id:
        raise HTTPException(404, "Record not found")
    db.delete(record)
    db.commit()
