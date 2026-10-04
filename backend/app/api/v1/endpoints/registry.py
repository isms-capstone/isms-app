from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.endpoints.customers import get_record, REGISTRY_EDITOR_ROLES
from app.api.v1.endpoints.products import require_product_admin, save_product_record
from app.db.models.customer import ChannelIdentity, Contact, Organization
from app.db.models.customer_context import CourseOrExam, Department
from app.db.models.product import Product, ProductInstance
from app.db.models.user import Team, User
from app.db.session import get_db
from app.schemas.customer import ContactCreate, OrganizationResponse
from app.schemas.customer_context import CourseResponse, DepartmentResponse
from app.schemas.product import InstanceResponse
from app.services.product_search import resolve_search_context

router = APIRouter(dependencies=[Depends(get_current_user)])


class TeamSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_team_id: int | None


class ContactChoice(ContactCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int


class CustomerChoice(BaseModel):
    organization: OrganizationResponse
    contact: ContactChoice | None = None


class CustomerSelection(BaseModel):
    organization: OrganizationResponse
    contact: ContactChoice | None = None
    instances: list[InstanceResponse]
    departments: list[DepartmentResponse]
    courses: list[CourseResponse]


@router.get("/registry/session")
def session(user: User = Depends(get_current_user)):
    name = user.role.name if user.role else None
    return {"username": user.username, "role": name,
            "can_edit_customers": name in REGISTRY_EDITOR_ROLES,
            "can_edit_products": name == "Admin"}


@router.get("/registry/teams")
def teams(db: Session = Depends(get_db)):
    # Use existing INFRA teams; do not create a competing ADM team registry.
    return [{"id": team.id, "name": team.name} for team in db.scalars(select(Team).order_by(Team.name, Team.id))]


@router.put("/products/{product_id}/default-team", dependencies=[Depends(require_product_admin)])
def default_team(product_id: int, body: TeamSelection, db: Session = Depends(get_db)):
    product = get_record(db, Product, product_id)
    if body.default_team_id is not None:
        get_record(db, Team, body.default_team_id)
    product.default_team_id = body.default_team_id
    save_product_record(db, product)
    return {"product_id": product.id, "default_team_id": product.default_team_id}


@router.get("/products/{product_id}/routing-context")
def routing_context(product_id: int, db: Session = Depends(get_db)):
    product = get_record(db, Product, product_id)
    return {"product_id": product.id, "default_team_id": product.default_team_id}


@router.get("/customers/autocomplete", response_model=list[CustomerChoice])
def autocomplete(q: str = Query(..., min_length=1, max_length=255), limit: int = Query(10, ge=1, le=20),
                 db: Session = Depends(get_db)):
    term = q.strip()
    if not term:
        return []
    orgs = db.scalars(select(Organization).where(Organization.is_active.is_(True),
        Organization.name.contains(term, autoescape=True)).order_by(Organization.name, Organization.id).limit(limit)).all()
    contacts = db.scalars(select(Contact).join(Organization).where(
        Contact.is_active.is_(True), Organization.is_active.is_(True), or_(
            Contact.name.contains(term, autoescape=True),
            Contact.channels.any(ChannelIdentity.value.contains(term, autoescape=True))
        )).order_by(Contact.name, Contact.id).limit(limit)).all()
    # Interleave both types so many name matches cannot hide all contact results.
    needed = {contact.organization_id for contact in contacts}
    parents = {org.id: org for org in db.scalars(select(Organization).where(Organization.id.in_(needed)))} if needed else {}
    choices = []
    for i in range(max(len(orgs), len(contacts))):
        if i < len(orgs):
            choices.append(CustomerChoice(organization=OrganizationResponse.model_validate(orgs[i])))
        if i < len(contacts):
            contact = contacts[i]
            choices.append(CustomerChoice(organization=OrganizationResponse.model_validate(parents[contact.organization_id]),
                                          contact=ContactChoice.model_validate(contact)))
    return choices[:limit]


@router.get("/customers/organizations/{organization_id}/selection-context", response_model=CustomerSelection)
def selection_context(organization_id: int, contact_id: int | None = None, db: Session = Depends(get_db)):
    organization = get_record(db, Organization, organization_id)
    if not organization.is_active:
        raise HTTPException(409, "Organization is inactive")
    contact = None
    if contact_id is not None:
        contact = get_record(db, Contact, contact_id)
        if contact.organization_id != organization_id:
            raise HTTPException(404, "Contact not found in this organization")
        if not contact.is_active:
            raise HTTPException(409, "Contact is inactive")
    instances = db.scalars(select(ProductInstance).join(Product).where(
        ProductInstance.organization_id == organization_id, ProductInstance.is_active.is_(True),
        Product.is_active.is_(True)).order_by(ProductInstance.name, ProductInstance.id)).all()
    departments = db.scalars(select(Department).where(Department.organization_id == organization_id,
        Department.is_active.is_(True)).order_by(Department.name, Department.id)).all()
    courses = db.scalars(select(CourseOrExam).where(CourseOrExam.organization_id == organization_id,
        CourseOrExam.is_active.is_(True)).order_by(CourseOrExam.name, CourseOrExam.id)).all()
    return CustomerSelection(organization=OrganizationResponse.model_validate(organization),
        contact=ContactChoice.model_validate(contact) if contact else None,
        instances=[InstanceResponse.model_validate(row) for row in instances],
        departments=[DepartmentResponse.model_validate(row) for row in departments],
        courses=[CourseResponse.model_validate(row) for row in courses])


@router.get("/registry/search-context")
def search_context(product_instance_id: int | None = Query(None, gt=0), db: Session = Depends(get_db)):
    try:
        context = resolve_search_context(db, product_instance_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from None
    return {"product_instance_id": context.product_instance_id,
            "preferred_product_id": context.preferred_product_id, "include_other_products": True}
