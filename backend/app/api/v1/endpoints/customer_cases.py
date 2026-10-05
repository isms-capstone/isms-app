"""Customer case overview (P1-CUSPRD-04)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.endpoints.customers import get_record
from app.db.models.customer import Organization
from app.db.models.master_data import Module, ProblemType, Product, Symptom
from app.db.models.product import ProductInstance
from app.db.models.ticket import OPEN_STATUSES, Ticket
from app.db.session import get_db

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get('/customers/organizations/{organization_id}/case-summary')
def summary(organization_id: int, db: Session = Depends(get_db)):
    get_record(db, Organization, organization_id)
    count = db.scalar(select(func.count()).select_from(Ticket).where(
        Ticket.organization_id == organization_id, Ticket.status.in_(OPEN_STATUSES)))
    return {'organization_id': organization_id, 'open_count': count}


@router.get('/customers/organizations/{organization_id}/problem-history')
def history(organization_id: int, offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
            db: Session = Depends(get_db)):
    get_record(db, Organization, organization_id)
    frequency = func.count(Ticket.id).label('frequency')
    last_reported = func.max(Ticket.reported_at).label('last_reported_at')
    query = (select(Product.id.label('product_id'), Product.name.label('product_name'),
                    Module.id.label('module_id'), Module.name.label('module_name'),
                    ProblemType.id.label('category_id'), ProblemType.name.label('category_name'),
                    Symptom.id.label('symptom_id'), Symptom.name.label('symptom_name'), frequency, last_reported)
             .select_from(Ticket).outerjoin(ProductInstance, Ticket.product_instance_id == ProductInstance.id)
             .outerjoin(Product, ProductInstance.product_id == Product.id)
             .outerjoin(Module, Ticket.module_id == Module.id)
             .outerjoin(ProblemType, Ticket.category_id == ProblemType.id)
             .outerjoin(Symptom, Ticket.symptom_id == Symptom.id)
             .where(Ticket.organization_id == organization_id,
                    Ticket.status.not_in(['DRAFT', 'DUPLICATE', 'CANCELLED']))
             .group_by(Product.id, Product.name, Module.id, Module.name, ProblemType.id, ProblemType.name,
                       Symptom.id, Symptom.name)
             .order_by(frequency.desc(), last_reported.desc(), Product.id, Module.id, ProblemType.id, Symptom.id)
             .offset(offset).limit(limit))
    from datetime import timezone
    results = []
    for row in db.execute(query).mappings():
        result = dict(row)
        result['last_reported_at'] = result['last_reported_at'].replace(tzinfo=timezone.utc)
        results.append(result)
    return results
