from datetime import date
from typing import Optional, Type

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models.master_data import (
    BusinessCalendar,
    BusinessHoliday,
    SlaPolicy,
    SlaPolicyRule,
)
from app.db.session import get_db
from app.schemas.master_data import (
    BusinessCalendarCreate,
    BusinessCalendarOut,
    BusinessCalendarUpdate,
    BusinessHolidayCreate,
    BusinessHolidayOut,
    BusinessHolidayUpdate,
    SlaPolicyCreate,
    SlaPolicyOut,
    SlaPolicyRuleCreate,
    SlaPolicyRuleOut,
    SlaPolicyRuleUpdate,
    SlaPolicyUpdate,
)

router = APIRouter(prefix="/admin/master-data", tags=["SLA & Business Calendar"])


def _get_or_404(db: Session, model: Type, item_id: int, label: str):
    item = db.query(model).filter(model.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return item


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate or conflicting master data") from exc


def _patch(item, data: dict) -> None:
    for field, value in data.items():
        setattr(item, field, value)


@router.get("/sla-policies", response_model=list[SlaPolicyOut], dependencies=[Depends(require_admin)])
def list_sla_policies(
    active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(SlaPolicy)
    if active is not None:
        query = query.filter(SlaPolicy.is_active.is_(active))
    return query.order_by(SlaPolicy.id).all()


@router.post("/sla-policies", response_model=SlaPolicyOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_sla_policy(body: SlaPolicyCreate, db: Session = Depends(get_db)):
    item = SlaPolicy(**body.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.patch("/sla-policies/{item_id}", response_model=SlaPolicyOut, dependencies=[Depends(require_admin)])
def update_sla_policy(item_id: int, body: SlaPolicyUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(db, SlaPolicy, item_id, "SLA Policy")
    _patch(item, body.model_dump(exclude_unset=True))
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/sla-policies/{item_id}", response_model=SlaPolicyOut, dependencies=[Depends(require_admin)])
def disable_sla_policy(item_id: int, db: Session = Depends(get_db)):
    item = _get_or_404(db, SlaPolicy, item_id, "SLA Policy")
    item.is_active = False
    _commit(db)
    db.refresh(item)
    return item


@router.get("/sla-policies/{policy_id}/rules", response_model=list[SlaPolicyRuleOut], dependencies=[Depends(require_admin)])
def list_sla_rules(
    policy_id: int,
    active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    _get_or_404(db, SlaPolicy, policy_id, "SLA Policy")
    query = db.query(SlaPolicyRule).filter(SlaPolicyRule.sla_policy_id == policy_id)
    if active is not None:
        query = query.filter(SlaPolicyRule.is_active.is_(active))
    return query.order_by(SlaPolicyRule.severity).all()


@router.post("/sla-policies/{policy_id}/rules", response_model=SlaPolicyRuleOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_sla_rule(policy_id: int, body: SlaPolicyRuleCreate, db: Session = Depends(get_db)):
    _get_or_404(db, SlaPolicy, policy_id, "SLA Policy")
    if body.resolution_max_value < body.resolution_min_value:
        raise HTTPException(status_code=422, detail="resolution_max_value must be >= resolution_min_value")
    item = SlaPolicyRule(sla_policy_id=policy_id, **body.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.patch("/sla-policies/{policy_id}/rules/{rule_id}", response_model=SlaPolicyRuleOut, dependencies=[Depends(require_admin)])
def update_sla_rule(policy_id: int, rule_id: int, body: SlaPolicyRuleUpdate, db: Session = Depends(get_db)):
    _get_or_404(db, SlaPolicy, policy_id, "SLA Policy")
    item = db.query(SlaPolicyRule).filter(
        SlaPolicyRule.id == rule_id,
        SlaPolicyRule.sla_policy_id == policy_id,
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="SLA Policy Rule not found")

    data = body.model_dump(exclude_unset=True)
    min_value = data.get("resolution_min_value", item.resolution_min_value)
    max_value = data.get("resolution_max_value", item.resolution_max_value)
    if max_value < min_value:
        raise HTTPException(status_code=422, detail="resolution_max_value must be >= resolution_min_value")

    _patch(item, data)
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/sla-policies/{policy_id}/rules/{rule_id}", response_model=SlaPolicyRuleOut, dependencies=[Depends(require_admin)])
def disable_sla_rule(policy_id: int, rule_id: int, db: Session = Depends(get_db)):
    _get_or_404(db, SlaPolicy, policy_id, "SLA Policy")
    item = db.query(SlaPolicyRule).filter(
        SlaPolicyRule.id == rule_id,
        SlaPolicyRule.sla_policy_id == policy_id,
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="SLA Policy Rule not found")
    item.is_active = False
    _commit(db)
    db.refresh(item)
    return item


@router.get("/business-calendars", response_model=list[BusinessCalendarOut], dependencies=[Depends(require_admin)])
def list_business_calendars(
    active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(BusinessCalendar)
    if active is not None:
        query = query.filter(BusinessCalendar.is_active.is_(active))
    return query.order_by(BusinessCalendar.id).all()


@router.post("/business-calendars", response_model=BusinessCalendarOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_business_calendar(body: BusinessCalendarCreate, db: Session = Depends(get_db)):
    if body.work_end_time <= body.work_start_time:
        raise HTTPException(status_code=422, detail="work_end_time must be later than work_start_time")
    item = BusinessCalendar(**body.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.patch("/business-calendars/{item_id}", response_model=BusinessCalendarOut, dependencies=[Depends(require_admin)])
def update_business_calendar(item_id: int, body: BusinessCalendarUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(db, BusinessCalendar, item_id, "Business Calendar")
    data = body.model_dump(exclude_unset=True)
    start = data.get("work_start_time", item.work_start_time)
    end = data.get("work_end_time", item.work_end_time)
    if end <= start:
        raise HTTPException(status_code=422, detail="work_end_time must be later than work_start_time")
    _patch(item, data)
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/business-calendars/{item_id}", response_model=BusinessCalendarOut, dependencies=[Depends(require_admin)])
def disable_business_calendar(item_id: int, db: Session = Depends(get_db)):
    item = _get_or_404(db, BusinessCalendar, item_id, "Business Calendar")
    item.is_active = False
    _commit(db)
    db.refresh(item)
    return item


@router.get("/business-calendars/{calendar_id}/holidays", response_model=list[BusinessHolidayOut], dependencies=[Depends(require_admin)])
def list_business_holidays(
    calendar_id: int,
    year: Optional[int] = Query(None, ge=2000, le=2100),
    active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    _get_or_404(db, BusinessCalendar, calendar_id, "Business Calendar")
    query = db.query(BusinessHoliday).filter(BusinessHoliday.business_calendar_id == calendar_id)
    if year is not None:
        query = query.filter(
            BusinessHoliday.holiday_date >= date(year, 1, 1),
            BusinessHoliday.holiday_date < date(year + 1, 1, 1),
        )
    if active is not None:
        query = query.filter(BusinessHoliday.is_active.is_(active))
    return query.order_by(BusinessHoliday.holiday_date, BusinessHoliday.id).all()


@router.post("/business-calendars/{calendar_id}/holidays", response_model=BusinessHolidayOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_business_holiday(calendar_id: int, body: BusinessHolidayCreate, db: Session = Depends(get_db)):
    _get_or_404(db, BusinessCalendar, calendar_id, "Business Calendar")
    item = BusinessHoliday(business_calendar_id=calendar_id, **body.model_dump())
    db.add(item)
    _commit(db)
    db.refresh(item)
    return item


@router.patch("/business-calendars/{calendar_id}/holidays/{holiday_id}", response_model=BusinessHolidayOut, dependencies=[Depends(require_admin)])
def update_business_holiday(calendar_id: int, holiday_id: int, body: BusinessHolidayUpdate, db: Session = Depends(get_db)):
    _get_or_404(db, BusinessCalendar, calendar_id, "Business Calendar")
    item = db.query(BusinessHoliday).filter(
        BusinessHoliday.id == holiday_id,
        BusinessHoliday.business_calendar_id == calendar_id,
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Business Holiday not found")
    _patch(item, body.model_dump(exclude_unset=True))
    _commit(db)
    db.refresh(item)
    return item


@router.delete("/business-calendars/{calendar_id}/holidays/{holiday_id}", response_model=BusinessHolidayOut, dependencies=[Depends(require_admin)])
def disable_business_holiday(calendar_id: int, holiday_id: int, db: Session = Depends(get_db)):
    _get_or_404(db, BusinessCalendar, calendar_id, "Business Calendar")
    item = db.query(BusinessHoliday).filter(
        BusinessHoliday.id == holiday_id,
        BusinessHoliday.business_calendar_id == calendar_id,
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Business Holiday not found")
    item.is_active = False
    _commit(db)
    db.refresh(item)
    return item
