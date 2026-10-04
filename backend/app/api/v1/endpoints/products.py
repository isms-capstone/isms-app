from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.api.v1.endpoints.customers import get_record, require_registry_editor
from app.db.models.customer import Organization
from app.db.models.product import Product, ProductInstance, ProductModule
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.product import (
    InstanceCreate, InstanceResponse, ModuleCreate, ModuleResponse,
    ProductCreate, ProductResponse,
)


def require_product_admin(user: User = Depends(get_current_user)):
    if not user.role or user.role.name != "Admin":
        raise HTTPException(403, "Only Admin can change the product catalogue")
    return user


router = APIRouter(dependencies=[Depends(get_current_user)])


def save_product_record(db: Session, record):
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Code already exists in this registry scope") from None
    db.refresh(record)
    return record


def replace_record(db, record, body):
    # JSON mode serializes HttpUrl to a string accepted by SQLAlchemy.
    for key, value in body.model_dump(mode="json").items():
        setattr(record, key, value)
    return save_product_record(db, record)


@router.get("/products", response_model=list[ProductResponse])
def products(q: str = Query("", max_length=255), is_active: bool | None = None,
             offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
             db: Session = Depends(get_db)):
    query = select(Product).options(selectinload(Product.modules))
    if q.strip():
        term = q.strip()
        query = query.where(or_(Product.name.contains(term, autoescape=True),
                               Product.code.contains(term, autoescape=True)))
    if is_active is not None:
        query = query.where(Product.is_active == is_active)
    return db.scalars(query.order_by(Product.name, Product.id).offset(offset).limit(limit)).all()


@router.post("/products", response_model=ProductResponse, status_code=201,
             dependencies=[Depends(require_product_admin)])
def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    return save_product_record(db, Product(**body.model_dump()))


@router.get("/products/{product_id}", response_model=ProductResponse)
def product(product_id: int, db: Session = Depends(get_db)):
    return get_record(db, Product, product_id)


@router.put("/products/{product_id}", response_model=ProductResponse,
            dependencies=[Depends(require_product_admin)])
def update_product(product_id: int, body: ProductCreate, db: Session = Depends(get_db)):
    return replace_record(db, get_record(db, Product, product_id), body)


@router.get("/products/{product_id}/modules", response_model=list[ModuleResponse])
def modules(product_id: int, is_active: bool | None = None,
            offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
            db: Session = Depends(get_db)):
    get_record(db, Product, product_id)
    query = select(ProductModule).where(ProductModule.product_id == product_id)
    if is_active is not None:
        query = query.where(ProductModule.is_active == is_active)
    return db.scalars(query.order_by(ProductModule.name, ProductModule.id).offset(offset).limit(limit)).all()


@router.post("/products/{product_id}/modules", response_model=ModuleResponse, status_code=201,
             dependencies=[Depends(require_product_admin)])
def create_module(product_id: int, body: ModuleCreate, db: Session = Depends(get_db)):
    get_record(db, Product, product_id)
    return save_product_record(db, ProductModule(product_id=product_id, **body.model_dump()))


@router.put("/products/{product_id}/modules/{module_id}", response_model=ModuleResponse,
            dependencies=[Depends(require_product_admin)])
def update_module(product_id: int, module_id: int, body: ModuleCreate, db: Session = Depends(get_db)):
    record = get_record(db, ProductModule, module_id)
    if record.product_id != product_id:
        raise HTTPException(404, "Record not found")
    return replace_record(db, record, body)


@router.get("/product-instances", response_model=list[InstanceResponse])
def instances(organization_id: int | None = None, product_id: int | None = None,
              is_active: bool | None = None, q: str = Query("", max_length=255),
              offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
              db: Session = Depends(get_db)):
    query = select(ProductInstance)
    if organization_id is not None:
        get_record(db, Organization, organization_id)
        query = query.where(ProductInstance.organization_id == organization_id)
    if product_id is not None:
        get_record(db, Product, product_id)
        query = query.where(ProductInstance.product_id == product_id)
    if is_active is not None:
        query = query.where(ProductInstance.is_active == is_active)
    if q.strip():
        term = q.strip()
        query = query.where(or_(ProductInstance.name.contains(term, autoescape=True),
                               ProductInstance.code.contains(term, autoescape=True)))
    return db.scalars(query.order_by(ProductInstance.name, ProductInstance.id).offset(offset).limit(limit)).all()


@router.post("/organizations/{organization_id}/products/{product_id}/instances",
             response_model=InstanceResponse, status_code=201,
             dependencies=[Depends(require_registry_editor)])
def create_instance(organization_id: int, product_id: int, body: InstanceCreate,
                    db: Session = Depends(get_db)):
    get_record(db, Organization, organization_id)
    get_record(db, Product, product_id)
    return save_product_record(db, ProductInstance(organization_id=organization_id,
                               product_id=product_id, **body.model_dump(mode="json")))


@router.get("/product-instances/{instance_id}", response_model=InstanceResponse)
def instance(instance_id: int, db: Session = Depends(get_db)):
    return get_record(db, ProductInstance, instance_id)


@router.put("/product-instances/{instance_id}", response_model=InstanceResponse,
            dependencies=[Depends(require_registry_editor)])
def update_instance(instance_id: int, body: InstanceCreate, db: Session = Depends(get_db)):
    # Organization/product references stay fixed to preserve future ticket links.
    return replace_record(db, get_record(db, ProductInstance, instance_id), body)
