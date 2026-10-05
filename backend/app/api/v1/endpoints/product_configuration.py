"""Product-scoped category options and SLA association, using ADM master data."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_admin
from app.api.v1.endpoints.customers import get_record
from app.api.v1.endpoints.products import save_product_record
from app.db.models.master_data import Product, Module, Symptom, ServiceStage, ProblemType, SlaPolicy
from app.db.session import get_db
from app.schemas.master_data import SlaPolicyOut, SlaPolicyRuleOut
from app.schemas.product import ProductResponse

router = APIRouter(dependencies=[Depends(get_current_user)])


class SlaAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sla_policy_id: int | None = Field(ge=1)


class CaseOptionsSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    module_id: int | None = Field(default=None, ge=1)
    symptom_id: int | None = Field(default=None, ge=1)
    service_stage_id: int | None = Field(default=None, ge=1)
    problem_type_id: int | None = Field(default=None, ge=1)


@router.get('/registry/sla-policies', response_model=list[SlaPolicyOut], dependencies=[Depends(require_admin)])
def assignable_policies(db: Session = Depends(get_db)):
    return db.scalars(select(SlaPolicy).where(SlaPolicy.is_active.is_(True)).order_by(SlaPolicy.name, SlaPolicy.id)).all()


@router.put('/products/{product_id}/sla-policy', response_model=ProductResponse, dependencies=[Depends(require_admin)])
def assign_policy(product_id: int, body: SlaAssignment, db: Session = Depends(get_db)):
    product = get_record(db, Product, product_id)
    if body.sla_policy_id is not None:
        policy = get_record(db, SlaPolicy, body.sla_policy_id)
        if not policy.is_active:
            raise HTTPException(409, 'Cannot assign an inactive SLA policy')
    product.sla_policy_id = body.sla_policy_id
    return save_product_record(db, product)


def case_options(db, product_id):
    product = get_record(db, Product, product_id)
    if not product.is_active:
        raise HTTPException(409, 'Product is inactive')
    def rows(model):
        return db.scalars(select(model).where(model.product_id == product_id, model.is_active.is_(True))
                          .order_by(model.name, model.id)).all()
    modules = rows(Module)
    module_ids = [row.id for row in modules]
    problems = db.scalars(select(ProblemType).where(ProblemType.module_id.in_(module_ids),
                         ProblemType.is_active.is_(True)).order_by(ProblemType.name, ProblemType.id)).all()
    policy = db.scalar(select(SlaPolicy).options(selectinload(SlaPolicy.rules))
                       .where(SlaPolicy.id == product.sla_policy_id, SlaPolicy.is_active.is_(True)))
    return product, modules, rows(Symptom), rows(ServiceStage), problems, policy


@router.get('/products/{product_id}/case-options')
def product_case_options(product_id: int, db: Session = Depends(get_db)):
    product, modules, symptoms, stages, problems, policy = case_options(db, product_id)
    def options(rows):
        return [{'id': row.id, 'name': row.name} for row in rows]
    return {'product_id': product.id, 'modules': options(modules), 'symptoms': options(symptoms),
            'service_stages': [{'id': row.id, 'name': row.name, 'sort_order': row.sort_order}
                               for row in sorted(stages, key=lambda row: (row.sort_order, row.id))],
            'problem_types': [{'id': row.id, 'name': row.name, 'module_id': row.module_id} for row in problems],
            'configured_sla_policy_id': product.sla_policy_id,
            'sla_policy': None if policy is None else {
                'id': policy.id, 'name': policy.name,
                'rules': [SlaPolicyRuleOut.model_validate(row).model_dump() for row in policy.rules if row.is_active]}}


@router.post('/products/{product_id}/validate-case-options', response_model=CaseOptionsSelection)
def validate_selection(product_id: int, body: CaseOptionsSelection, db: Session = Depends(get_db)):
    _, modules, symptoms, stages, problems, _ = case_options(db, product_id)
    for field, rows in [('module_id', modules), ('symptom_id', symptoms),
                        ('service_stage_id', stages), ('problem_type_id', problems)]:
        selected = getattr(body, field)
        if selected is not None and selected not in {row.id for row in rows}:
            raise HTTPException(422, f'{field} is inactive or belongs to another product')
    if body.problem_type_id is not None:
        problem = next(row for row in problems if row.id == body.problem_type_id)
        if problem.module_id != body.module_id:
            raise HTTPException(422, 'problem_type_id must belong to the selected module')
    return body
