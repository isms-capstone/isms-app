"""Run only against the disposable CI MariaDB created by registry-mariadb-tests."""
import os
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine, get_db
from app.db.models.user import Team


@pytest.mark.skipif(os.getenv("REGISTRY_MARIADB_QA") != "1", reason="Requires isolated CI MariaDB")
def test_migrated_mariadb_registry_workflow():
    assert settings.MARIADB_DB == "isms_registry_qa", "Never run against a customer database"
    assert engine.dialect.name == "mysql"
    assert "exam_window" in inspect(engine).get_table_names()
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    def database():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role=SimpleNamespace(name="Admin"))
    with TestClient(app) as client:
        def post(path, body, status=201):
            result = client.post('/api/v1' + path, json=body)
            assert result.status_code == status, result.text
            return result.json()
        org = post('/customers/organizations', {'name': 'มหาวิทยาลัย QA'})['id']
        other = post('/customers/organizations', {'name': 'Other QA'})['id']
        contact = post(f'/customers/organizations/{org}/contacts', {'name': 'อาจารย์ QA'})['id']
        post(f'/customers/contacts/{contact}/channels', {'channel_type': 'email', 'value': 'qa@example.org'})
        assert client.get('/api/v1/customers/organizations?q=มหาวิทยาลัย').json()[0]['id'] == org
        product = post('/products', {'code': 'examqa', 'name': 'Exam QA'})['id']
        post(f'/products/{product}/modules', {'code': 'teacher', 'name': 'Teacher'})
        instance = post(f'/organizations/{org}/products/{product}/instances', {'code': 'production', 'name': 'QA', 'version': '1.0', 'environment': 'production', 'url': 'https://example.org'})['id']
        dept = post(f'/customers/organizations/{org}/departments', {'name': 'Medicine'})['id']
        course = post(f'/customers/organizations/{org}/courses', {'name': ' MED101 '})['id']
        assert post(f'/customers/organizations/{org}/courses', {'name': 'med101'}, 200)['id'] == course
        window = {'name': 'Final', 'department_id': dept, 'starts_at': '2026-10-05T09:00:00+07:00', 'ends_at': '2026-10-05T12:00:00+07:00'}
        post(f'/customers/organizations/{org}/exam-windows', window)
        post(f'/customers/organizations/{other}/exam-windows', window, 404)
        assert client.patch(f'/api/v1/customers/organizations/{org}/contract', json={'contract_start_date': '2026-01-01', 'contract_end_date': '2026-12-31'}).status_code == 200
        with Session(engine) as db:
            team = Team(name='QA Support')
            db.add(team); db.commit(); db.refresh(team)
            team_id = team.id
        assert client.put(f'/api/v1/products/{product}/default-team', json={'default_team_id': team_id}).status_code == 200
        assert client.get(f'/api/v1/customers/organizations/{org}/selection-context?contact_id={contact}').json()['instances'][0]['id'] == instance
        assert client.get(f'/api/v1/registry/search-context?product_instance_id={instance}').json()['preferred_product_id'] == product
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role=SimpleNamespace(name='Auditor'))
        post('/products', {'code': 'denied', 'name': 'Denied'}, 403)
