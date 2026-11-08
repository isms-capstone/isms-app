"""Explicit, idempotent CAT acceptance catalogue; never runs at app startup.

Run from backend: python scripts/seed_cat_qa.py --apply
Creates only clearly labelled QA data, without changing existing customers,
cases, accounts, or inactive configuration. No ticket is created.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.db.models  # register all FK targets
from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models.customer import Organization
from app.db.models.product import ProductInstance
from app.db.models.master_data import Product, Module, Symptom, ServiceStage, ProblemType, CauseCode, SolutionCode


def seed(db):
    created = 0

    def ensure(model, keys, **values):
        nonlocal created
        row = db.scalar(select(model).filter_by(**keys))
        if row is None:
            row = model(**keys, **values)
            db.add(row)
            db.flush()
            created += 1
        elif not row.is_active:
            raise RuntimeError(f'{model.__name__} QA data is inactive; ask Admin to review it')
        return row

    org = ensure(Organization, {'name': 'QA CAT - ทดสอบหมวดหมู่'})
    for code, name, modules, symptom, stage in (
        ('qa-cat-a', 'QA CAT A - Exam', ('Teacher', 'Student'), 'Download failure', 'During exam'),
        ('qa-cat-b', 'QA CAT B - Clinic', ('Clinic',), 'Mapping error', 'General'),
    ):
        product = ensure(Product, {'code': code}, name=name, description='CAT acceptance test data')
        ensure(ProductInstance, {'organization_id': org.id, 'product_id': product.id, 'code': code},
               name='QA CAT Instance ' + code[-1].upper(), version='1.0', environment='test', url='https://example.invalid')
        for module_name in modules:
            module = ensure(Module, {'product_id': product.id, 'name': module_name}, code=module_name.lower())
            ensure(ProblemType, {'module_id': module.id, 'name': module_name + ' access'})
        ensure(Symptom, {'product_id': product.id, 'name': symptom})
        ensure(ServiceStage, {'product_id': product.id, 'name': stage})
    ensure(CauseCode, {'code': 'QA-CAT-CONFIG'}, name='QA CAT - ตั้งค่าระบบไม่ครบ')
    ensure(SolutionCode, {'code': 'QA-CAT-RECONFIG'}, name='QA CAT - ปรับตั้งค่าและทดสอบซ้ำ')
    return created


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Explicitly save the labelled QA catalogue')
    args = parser.parse_args()
    if not args.apply:
        parser.error('Pass --apply to create the isolated QA catalogue')
    with SessionLocal() as db:
        try:
            count = seed(db)
            db.commit()
            print(f'Created {count} QA records. Select customer: QA CAT - ทดสอบหมวดหมู่')
        except Exception:
            db.rollback()
            raise
