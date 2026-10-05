from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_any_authenticated
from app.db.session import get_db
from app.db.models.master_data import (
    Product, Module, ProblemType, Symptom, ServiceStage,
    TicketType, CauseCode, SolutionCode, CaseTemplate, CannedMessage,
)
from app.schemas.master_data import (
    ProductCreate, ProductUpdate, ProductOut,
    MasterDataBase, MasterDataUpdate, MasterDataOut,
    ProductRefBase, ProductRefUpdate, ProductRefOut,
    ModuleRefBase, ModuleRefUpdate, ModuleRefOut,
    ServiceStageCreate, ServiceStageUpdate, ServiceStageOut,
    CodeCreate, CodeUpdate, CodeOut,
    ModuleCreate, ModuleUpdate,
    ProblemTypeCreate, ProblemTypeUpdate,
    CaseTemplateCreate, CaseTemplateUpdate, CaseTemplateOut,
    CannedMessageCreate, CannedMessageUpdate, CannedMessageOut,
)

router = APIRouter(prefix="/admin/master-data", tags=["Admin - Master Data"])


def _get_or_404(db: Session, model, item_id: int, label: str):
    item = db.get(model, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{label} not found")
    return item


def _commit(db: Session):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Duplicate or referenced master-data value") from exc


def _list(db: Session, model, active: Optional[bool]):
    query = db.query(model)
    if active is not None:
        query = query.filter(model.is_active.is_(active))
    return query.order_by(model.id).all()


def _patch_common(item, data):
    for field, value in data.items():
        if value is not None or field == "is_active":
            setattr(item, field, value)


# Product
@router.get("/products", response_model=list[ProductOut], dependencies=[Depends(require_admin)])
def list_products(active: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    return _list(db, Product, active)


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    item = Product(**body.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.patch("/products/{item_id}", response_model=ProductOut, dependencies=[Depends(require_admin)])
def update_product(item_id: int, body: ProductUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(db, Product, item_id, "Product")
    _patch_common(item, body.model_dump(exclude_unset=True))
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/products/{item_id}", response_model=ProductOut, dependencies=[Depends(require_admin)])
def disable_product(item_id: int, db: Session = Depends(get_db)):
    item = _get_or_404(db, Product, item_id, "Product")
    item.is_active = False
    _commit(db)
    db.refresh(item)
    return item


# Product -> Module
@router.get("/modules", response_model=list[ProductRefOut], dependencies=[Depends(require_admin)])
def list_modules(product_id: Optional[int] = Query(None), active: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Module)
    if product_id is not None:
        query = query.filter(Module.product_id == product_id)
    if active is not None:
        query = query.filter(Module.is_active.is_(active))
    return query.order_by(Module.id).all()


@router.post("/modules", response_model=ProductRefOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_module(body: ModuleCreate, db: Session = Depends(get_db)):
    _get_or_404(db, Product, body.product_id, "Product")
    item = Module(**body.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.patch("/modules/{item_id}", response_model=ProductRefOut, dependencies=[Depends(require_admin)])
def update_module(item_id: int, body: ModuleUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(db, Module, item_id, "Module")
    data = body.model_dump(exclude_unset=True)
    if "product_id" in data and data["product_id"] is not None:
        _get_or_404(db, Product, data["product_id"], "Product")
    _patch_common(item, data)
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/modules/{item_id}", response_model=ProductRefOut, dependencies=[Depends(require_admin)])
def disable_module(item_id: int, db: Session = Depends(get_db)):
    item = _get_or_404(db, Module, item_id, "Module")
    item.is_active = False
    _commit(db)
    db.refresh(item)
    return item


# Module -> Problem Type
@router.get("/problem-types", response_model=list[ModuleRefOut], dependencies=[Depends(require_admin)])
def list_problem_types(module_id: Optional[int] = Query(None), active: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    query = db.query(ProblemType)
    if module_id is not None:
        query = query.filter(ProblemType.module_id == module_id)
    if active is not None:
        query = query.filter(ProblemType.is_active.is_(active))
    return query.order_by(ProblemType.id).all()


@router.post("/problem-types", response_model=ModuleRefOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_problem_type(body: ProblemTypeCreate, db: Session = Depends(get_db)):
    _get_or_404(db, Module, body.module_id, "Module")
    item = ProblemType(module_id=body.module_id, name=body.name, description=body.description)
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.patch("/problem-types/{item_id}", response_model=ModuleRefOut, dependencies=[Depends(require_admin)])
def update_problem_type(item_id: int, body: ProblemTypeUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(db, ProblemType, item_id, "Problem Type")
    data = body.model_dump(exclude_unset=True)
    if "module_id" in data and data["module_id"] is not None:
        _get_or_404(db, Module, data["module_id"], "Module")
    _patch_common(item, data)
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/problem-types/{item_id}", response_model=ModuleRefOut, dependencies=[Depends(require_admin)])
def disable_problem_type(item_id: int, db: Session = Depends(get_db)):
    item = _get_or_404(db, ProblemType, item_id, "Problem Type")
    item.is_active = False
    _commit(db)
    db.refresh(item)
    return item


# Product-scoped Symptom
@router.get("/symptoms", response_model=list[ProductRefOut], dependencies=[Depends(require_admin)])
def list_symptoms(product_id: Optional[int] = Query(None), active: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Symptom)
    if product_id is not None:
        query = query.filter(Symptom.product_id == product_id)
    if active is not None:
        query = query.filter(Symptom.is_active.is_(active))
    return query.order_by(Symptom.id).all()


@router.post("/symptoms", response_model=ProductRefOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_symptom(body: ProductRefBase, db: Session = Depends(get_db)):
    _get_or_404(db, Product, body.product_id, "Product")
    item = Symptom(**body.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.patch("/symptoms/{item_id}", response_model=ProductRefOut, dependencies=[Depends(require_admin)])
def update_symptom(item_id: int, body: ProductRefUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(db, Symptom, item_id, "Symptom")
    data = body.model_dump(exclude_unset=True)
    if "product_id" in data and data["product_id"] is not None:
        _get_or_404(db, Product, data["product_id"], "Product")
    _patch_common(item, data)
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/symptoms/{item_id}", response_model=ProductRefOut, dependencies=[Depends(require_admin)])
def disable_symptom(item_id: int, db: Session = Depends(get_db)):
    item = _get_or_404(db, Symptom, item_id, "Symptom")
    item.is_active = False
    _commit(db)
    db.refresh(item)
    return item


# Product-scoped Service Stage
@router.get("/service-stages", response_model=list[ServiceStageOut], dependencies=[Depends(require_admin)])
def list_service_stages(product_id: Optional[int] = Query(None), active: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    query = db.query(ServiceStage)
    if product_id is not None:
        query = query.filter(ServiceStage.product_id == product_id)
    if active is not None:
        query = query.filter(ServiceStage.is_active.is_(active))
    return query.order_by(ServiceStage.sort_order, ServiceStage.id).all()


@router.post("/service-stages", response_model=ServiceStageOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_service_stage(body: ServiceStageCreate, db: Session = Depends(get_db)):
    _get_or_404(db, Product, body.product_id, "Product")
    item = ServiceStage(**body.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.patch("/service-stages/{item_id}", response_model=ServiceStageOut, dependencies=[Depends(require_admin)])
def update_service_stage(item_id: int, body: ServiceStageUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(db, ServiceStage, item_id, "Service Stage")
    data = body.model_dump(exclude_unset=True)
    if "product_id" in data and data["product_id"] is not None:
        _get_or_404(db, Product, data["product_id"], "Product")
    _patch_common(item, data)
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/service-stages/{item_id}", response_model=ServiceStageOut, dependencies=[Depends(require_admin)])
def disable_service_stage(item_id: int, db: Session = Depends(get_db)):
    item = _get_or_404(db, ServiceStage, item_id, "Service Stage")
    item.is_active = False
    _commit(db)
    db.refresh(item)
    return item


# Global Ticket Type / Cause / Solution
@router.get("/ticket-types", response_model=list[MasterDataOut], dependencies=[Depends(require_admin)])
def list_ticket_types(active: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    return _list(db, TicketType, active)


@router.post("/ticket-types", response_model=MasterDataOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_ticket_type(body: MasterDataBase, db: Session = Depends(get_db)):
    item = TicketType(**body.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.patch("/ticket-types/{item_id}", response_model=MasterDataOut, dependencies=[Depends(require_admin)])
def update_ticket_type(item_id: int, body: MasterDataUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(db, TicketType, item_id, "Ticket Type")
    _patch_common(item, body.model_dump(exclude_unset=True))
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/ticket-types/{item_id}", response_model=MasterDataOut, dependencies=[Depends(require_admin)])
def disable_ticket_type(item_id: int, db: Session = Depends(get_db)):
    item = _get_or_404(db, TicketType, item_id, "Ticket Type")
    item.is_active = False
    _commit(db)
    db.refresh(item)
    return item


def _code_routes(path: str, model, label: str):
    @router.get(f"/{path}", response_model=list[CodeOut], dependencies=[Depends(require_admin)], name=f"list_{path}")
    def list_codes(active: Optional[bool] = Query(None), db: Session = Depends(get_db)):
        return _list(db, model, active)

    @router.post(f"/{path}", response_model=CodeOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)], name=f"create_{path}")
    def create_code(body: CodeCreate, db: Session = Depends(get_db)):
        item = model(**body.model_dump())
        db.add(item)
        _commit(db)
        db.refresh(item)
        return item

    @router.patch(f"/{path}/{{item_id}}", response_model=CodeOut, dependencies=[Depends(require_admin)], name=f"update_{path}")
    def update_code(item_id: int, body: CodeUpdate, db: Session = Depends(get_db)):
        item = _get_or_404(db, model, item_id, label)
        _patch_common(item, body.model_dump(exclude_unset=True))
        _commit(db)
        db.refresh(item)
        return item

    @router.delete(f"/{path}/{{item_id}}", response_model=CodeOut, dependencies=[Depends(require_admin)], name=f"disable_{path}")
    def disable_code(item_id: int, db: Session = Depends(get_db)):
        item = _get_or_404(db, model, item_id, label)
        item.is_active = False
        _commit(db)
        db.refresh(item)
        return item


_code_routes("cause-codes", CauseCode, "Cause Code")
_code_routes("solution-codes", SolutionCode, "Solution Code")



def _validate_case_template_category(db: Session, product_id: int, module_id: int, problem_type_id: int):
    product = _get_or_404(db, Product, product_id, "Product")
    module = _get_or_404(db, Module, module_id, "Module")
    problem_type = _get_or_404(db, ProblemType, problem_type_id, "Problem Type")

    if not product.is_active or not module.is_active or not problem_type.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Case template category values must be active")
    if module.product_id != product.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Module does not belong to Product")
    if problem_type.module_id != module.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Problem Type does not belong to Module")


@router.get("/case-templates", response_model=list[CaseTemplateOut], dependencies=[Depends(require_admin)])
def list_case_templates(
    active: Optional[bool] = Query(None),
    product_id: Optional[int] = Query(None),
    module_id: Optional[int] = Query(None),
    problem_type_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(CaseTemplate)
    if active is not None:
        query = query.filter(CaseTemplate.is_active.is_(active))
    if product_id is not None:
        query = query.filter(CaseTemplate.product_id == product_id)
    if module_id is not None:
        query = query.filter(CaseTemplate.module_id == module_id)
    if problem_type_id is not None:
        query = query.filter(CaseTemplate.problem_type_id == problem_type_id)
    return query.order_by(CaseTemplate.id).all()


@router.post("/case-templates", response_model=CaseTemplateOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_case_template(body: CaseTemplateCreate, db: Session = Depends(get_db)):
    _validate_case_template_category(db, body.product_id, body.module_id, body.problem_type_id)
    item = CaseTemplate(**body.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.patch("/case-templates/{item_id}", response_model=CaseTemplateOut, dependencies=[Depends(require_admin)])
def update_case_template(item_id: int, body: CaseTemplateUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(db, CaseTemplate, item_id, "Case Template")
    data = body.model_dump(exclude_unset=True)
    category_fields_changed = any(
        field in data for field in ("product_id", "module_id", "problem_type_id")
    )
    if category_fields_changed or data.get("is_active") is True:
        product_id = data.get("product_id", item.product_id)
        module_id = data.get("module_id", item.module_id)
        problem_type_id = data.get("problem_type_id", item.problem_type_id)
        _validate_case_template_category(db, product_id, module_id, problem_type_id)
    _patch_common(item, data)
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/case-templates/{item_id}", response_model=CaseTemplateOut, dependencies=[Depends(require_admin)])
def disable_case_template(item_id: int, db: Session = Depends(get_db)):
    item = _get_or_404(db, CaseTemplate, item_id, "Case Template")
    item.is_active = False
    _commit(db)
    db.refresh(item)
    return item


@router.get("/canned-messages", response_model=list[CannedMessageOut], dependencies=[Depends(require_admin)])
def list_canned_messages(active: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    return _list(db, CannedMessage, active)


@router.post("/canned-messages", response_model=CannedMessageOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_canned_message(body: CannedMessageCreate, db: Session = Depends(get_db)):
    item = CannedMessage(**body.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.patch("/canned-messages/{item_id}", response_model=CannedMessageOut, dependencies=[Depends(require_admin)])
def update_canned_message(item_id: int, body: CannedMessageUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(db, CannedMessage, item_id, "Canned Message")
    _patch_common(item, body.model_dump(exclude_unset=True))
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/canned-messages/{item_id}", response_model=CannedMessageOut, dependencies=[Depends(require_admin)])
def disable_canned_message(item_id: int, db: Session = Depends(get_db)):
    item = _get_or_404(db, CannedMessage, item_id, "Canned Message")
    item.is_active = False
    _commit(db)
    db.refresh(item)
    return item


selection_router = APIRouter(prefix="/master-data", tags=["Master Data - Selection"])


@selection_router.get("/case-templates", response_model=list[CaseTemplateOut], dependencies=[Depends(require_any_authenticated)])
def list_active_case_templates_for_selection(
    product_id: Optional[int] = Query(None),
    module_id: Optional[int] = Query(None),
    problem_type_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(CaseTemplate)
        .join(Product, CaseTemplate.product_id == Product.id)
        .join(Module, CaseTemplate.module_id == Module.id)
        .join(ProblemType, CaseTemplate.problem_type_id == ProblemType.id)
        .filter(
            CaseTemplate.is_active.is_(True),
            Product.is_active.is_(True),
            Module.is_active.is_(True),
            ProblemType.is_active.is_(True),
        )
    )
    if product_id is not None:
        query = query.filter(CaseTemplate.product_id == product_id)
    if module_id is not None:
        query = query.filter(CaseTemplate.module_id == module_id)
    if problem_type_id is not None:
        query = query.filter(CaseTemplate.problem_type_id == problem_type_id)
    return query.order_by(CaseTemplate.name).all()


@selection_router.get("/canned-messages", response_model=list[CannedMessageOut], dependencies=[Depends(require_any_authenticated)])
def list_active_canned_messages_for_selection(db: Session = Depends(get_db)):
    return db.query(CannedMessage).filter(CannedMessage.is_active.is_(True)).order_by(CannedMessage.name).all()
