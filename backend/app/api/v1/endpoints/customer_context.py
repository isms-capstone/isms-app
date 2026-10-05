from datetime import datetime, timezone
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.endpoints.customers import get_record, require_registry_editor
from app.db.models.customer import Organization
from app.db.models.customer_context import CourseOrExam, Department, ExamWindow
from app.db.session import get_db
from app.schemas.customer_context import (
    ContractPatch, ContractResponse, CourseInput, CourseResponse,
    DepartmentInput, DepartmentResponse, ExamWindowInput, ExamWindowResponse,
)

router = APIRouter(dependencies=[Depends(get_current_user)])
write = [Depends(require_registry_editor)]


def normalized_name(value):
    return unicodedata.normalize("NFC", " ".join(value.split())).casefold()


def commit(db, record):
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Conflicting registry entry or invalid reference") from None
    db.refresh(record)
    return record


def scoped_record(db, model, organization_id, record_id):
    record = get_record(db, model, record_id)
    if record.organization_id != organization_id:
        raise HTTPException(404, "Record not found in this organization")
    return record


def named_values(body):
    values = body.model_dump()
    values["name"] = unicodedata.normalize("NFC", " ".join(body.name.split()))
    values["name_key"] = normalized_name(body.name)
    if len(values["name_key"]) > 255:
        raise HTTPException(422, "Normalized name exceeds 255 characters")
    return values


def list_named(db, model, organization_id, q, is_active, offset, limit, kind=None):
    get_record(db, Organization, organization_id)
    query = select(model).where(model.organization_id == organization_id)
    if q.strip():
        query = query.where(model.name_key.contains(normalized_name(q), autoescape=True))
    if is_active is not None:
        query = query.where(model.is_active == is_active)
    if kind is not None:
        query = query.where(model.kind == kind)
    return db.scalars(query.order_by(model.name, model.id).offset(offset).limit(limit)).all()


@router.get("/organizations/{organization_id}/departments", response_model=list[DepartmentResponse])
def departments(organization_id: int, q: str = Query("", max_length=255),
                is_active: bool | None = None, offset: int = Query(0, ge=0),
                limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    return list_named(db, Department, organization_id, q, is_active, offset, limit)


@router.post("/organizations/{organization_id}/departments", response_model=DepartmentResponse,
             status_code=201, dependencies=write)
def create_department(organization_id: int, body: DepartmentInput, db: Session = Depends(get_db)):
    get_record(db, Organization, organization_id)
    return commit(db, Department(organization_id=organization_id, **named_values(body)))


@router.put("/organizations/{organization_id}/departments/{record_id}", response_model=DepartmentResponse,
            dependencies=write)
def update_department(organization_id: int, record_id: int, body: DepartmentInput, db: Session = Depends(get_db)):
    record = scoped_record(db, Department, organization_id, record_id)
    for key, value in named_values(body).items():
        setattr(record, key, value)
    return commit(db, record)


@router.get("/organizations/{organization_id}/courses", response_model=list[CourseResponse])
def courses(organization_id: int, q: str = Query("", max_length=255),
            kind: str | None = Query(None, pattern="^(course|exam)$"), is_active: bool | None = None,
            offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    return list_named(db, CourseOrExam, organization_id, q, is_active, offset, limit, kind)


@router.post("/organizations/{organization_id}/courses", response_model=CourseResponse,
             status_code=201, dependencies=write)
def create_course(organization_id: int, body: CourseInput, response: Response, db: Session = Depends(get_db)):
    get_record(db, Organization, organization_id)
    values = named_values(body)
    query = select(CourseOrExam).where(CourseOrExam.organization_id == organization_id,
                                     CourseOrExam.kind == body.kind, CourseOrExam.name_key == values["name_key"])
    existing = db.scalar(query)
    if existing:
        if existing.is_active != body.is_active:
            raise HTTPException(409, "Entry exists with a different active state; update it explicitly")
        response.status_code = 200
        return existing
    record = CourseOrExam(organization_id=organization_id, **values)
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Concurrent capture of the same reusable text returns its canonical ID.
        existing = db.scalar(query)
        if existing and existing.is_active == body.is_active:
            response.status_code = 200
            return existing
        raise HTTPException(409, "Conflicting course/exam registry entry") from None
    db.refresh(record)
    return record


@router.put("/organizations/{organization_id}/courses/{record_id}", response_model=CourseResponse,
            dependencies=write)
def update_course(organization_id: int, record_id: int, body: CourseInput, db: Session = Depends(get_db)):
    record = scoped_record(db, CourseOrExam, organization_id, record_id)
    for key, value in named_values(body).items():
        setattr(record, key, value)
    return commit(db, record)


@router.get("/organizations/{organization_id}/contract", response_model=ContractResponse)
def contract(organization_id: int, db: Session = Depends(get_db)):
    return get_record(db, Organization, organization_id)


@router.patch("/organizations/{organization_id}/contract", response_model=ContractResponse, dependencies=write)
def update_contract(organization_id: int, body: ContractPatch, db: Session = Depends(get_db)):
    record = get_record(db, Organization, organization_id)
    values = body.model_dump(exclude_unset=True)
    start = values.get("contract_start_date", record.contract_start_date)
    end = values.get("contract_end_date", record.contract_end_date)
    if start is not None and end is not None and end < start:
        raise HTTPException(422, "Contract end must be on or after start")
    for key, value in values.items():
        setattr(record, key, value)
    return commit(db, record)


def window_values(db, organization_id, body):
    if body.department_id is not None:
        scoped_record(db, Department, organization_id, body.department_id)
    values = body.model_dump()
    for key in ("starts_at", "ends_at"):
        values[key] = values[key].astimezone(timezone.utc).replace(tzinfo=None)
    return values


@router.get("/organizations/{organization_id}/exam-windows", response_model=list[ExamWindowResponse])
def exam_windows(organization_id: int, active_at: datetime | None = None,
                 department_id: int | None = None, is_active: bool | None = None,
                 offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    get_record(db, Organization, organization_id)
    query = select(ExamWindow).where(ExamWindow.organization_id == organization_id)
    if department_id is not None:
        scoped_record(db, Department, organization_id, department_id)
        # Include organization-wide windows for department-specific SLA context.
        query = query.where((ExamWindow.department_id == department_id) | (ExamWindow.department_id.is_(None)))
    if is_active is not None:
        query = query.where(ExamWindow.is_active == is_active)
    if active_at is not None:
        if active_at.tzinfo is None or active_at.utcoffset() is None:
            raise HTTPException(422, "active_at must include timezone offset")
        moment = active_at.astimezone(timezone.utc).replace(tzinfo=None)
        query = query.where(ExamWindow.is_active.is_(True), ExamWindow.starts_at <= moment, ExamWindow.ends_at > moment)
    return db.scalars(query.order_by(ExamWindow.starts_at, ExamWindow.id).offset(offset).limit(limit)).all()


@router.post("/organizations/{organization_id}/exam-windows", response_model=ExamWindowResponse,
             status_code=201, dependencies=write)
def create_exam_window(organization_id: int, body: ExamWindowInput, db: Session = Depends(get_db)):
    get_record(db, Organization, organization_id)
    return commit(db, ExamWindow(organization_id=organization_id, **window_values(db, organization_id, body)))


@router.put("/organizations/{organization_id}/exam-windows/{record_id}", response_model=ExamWindowResponse,
            dependencies=write)
def update_exam_window(organization_id: int, record_id: int, body: ExamWindowInput, db: Session = Depends(get_db)):
    record = scoped_record(db, ExamWindow, organization_id, record_id)
    for key, value in window_values(db, organization_id, body).items():
        setattr(record, key, value)
    return commit(db, record)
