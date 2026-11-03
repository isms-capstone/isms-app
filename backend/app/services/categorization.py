"""SRS 13.1 and category audit/usage shared by capture and later edits."""
from fastapi import HTTPException
from sqlalchemy import select

from app.db.models.master_data import CauseCode, SolutionCode
from app.db.models.product import ProductInstance
from app.db.models.work_category import CategoryUsage, TicketAudit, TicketTag

AXES = ('module_id', 'category_id', 'symptom_id', 'service_stage_id', 'ticket_type_id')
USAGE_FIELDS = AXES + ('root_cause_code_id', 'resolution_code_id')
CATEGORY_FIELDS = AXES + ('product_instance_id', 'impact_scope', 'is_exam_window', 'severity',
    'severity_overridden_reason', 'root_cause_code_id', 'root_cause_detail',
    'resolution_code_id', 'resolution_detail')


def suggest_severity(impact, exam):
    return {'organization': ('S1', 'S2'), 'group': ('S2', 'S3'),
            'single_user': ('S3', 'S3'), 'non_disruptive': ('S3', 'S4')}[impact][0 if exam else 1]


def validate_assessment(values, db, allow_legacy=False):
    impact = values.get('impact_scope')
    severity = values.get('severity')
    if impact:
        suggested = suggest_severity(impact, values['is_exam_window'])
        if severity and severity != suggested and not values.get('severity_overridden_reason'):
            raise HTTPException(422, 'A reason is required when overriding the suggested severity')
        values['severity'] = severity or suggested
        if values['severity'] == suggested:
            values['severity_overridden_reason'] = None
    elif (severity or values.get('severity_overridden_reason')) and not allow_legacy:
        raise HTTPException(422, 'Select impact scope before assessing severity')
    for field, model in [('root_cause_code_id', CauseCode), ('resolution_code_id', SolutionCode)]:
        if values.get(field) is not None:
            row = db.get(model, values[field])
            if row is None or (not row.is_active and not allow_legacy):
                raise HTTPException(422, f'{field} is missing or inactive')


def snapshot(db, ticket):
    return {field: getattr(ticket, field) for field in CATEGORY_FIELDS} | {
        'tags': sorted(db.scalars(select(TicketTag.name).where(TicketTag.ticket_id == ticket.id)).all())}


def record_categories(db, ticket, user, tags, before=None):
    before = before or {}
    previous_tags = before.get('tags', [])
    if sorted(tags) != previous_tags:
        for row in db.scalars(select(TicketTag).where(TicketTag.ticket_id == ticket.id)).all():
            if row.name not in tags:
                db.delete(row)
        for tag in tags:
            if tag not in previous_tags:
                db.add(TicketTag(ticket_id=ticket.id, name=tag))
    after = {field: getattr(ticket, field) for field in CATEGORY_FIELDS} | {'tags': sorted(tags)}
    changes = {key: {'old': before.get(key), 'new': value} for key, value in after.items()
               if before.get(key) != value and (before or value not in (None, [], False))}
    if changes:
        db.add(TicketAudit(ticket_id=ticket.id, actor_id=user.id,
                           event='categorization_updated' if before else 'categorization_created', changes=changes))
    instance = db.get(ProductInstance, ticket.product_instance_id) if ticket.product_instance_id else None
    if instance:
        for axis in USAGE_FIELDS:
            value = getattr(ticket, axis)
            if value is not None and (value != before.get(axis) or ticket.product_instance_id != before.get('product_instance_id')):
                db.add(CategoryUsage(user_id=user.id, ticket_id=ticket.id, product_id=instance.product_id,
                                     axis=axis, option_id=value))
