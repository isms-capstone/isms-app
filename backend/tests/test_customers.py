import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.api.deps import get_current_user
from app.api.v1.endpoints.customers import router
from app.api.v1.endpoints.products import router as product_router
from app.api.v1.endpoints.customer_context import router as context_router
from app.api.v1.endpoints.registry import router as registry_router
from app.db.base_class import Base
from app.db.session import get_db


@pytest.fixture
def api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(router, prefix="/customers")
    app.include_router(product_router)
    app.include_router(context_router, prefix="/customers")
    app.include_router(registry_router)
    def database():
        with factory() as session:
            yield session
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role=SimpleNamespace(name="Agent"))
    with TestClient(app) as client:
        yield client, app
    engine.dispose()


def test_registry_search_and_multiple_channels(api):
    client, _ = api
    org = client.post("/customers/organizations", json={"name": "มหาวิทยาลัย TU"})
    assert org.status_code == 201
    org_id = org.json()["id"]
    contact = client.post(f"/customers/organizations/{org_id}/contacts", json={"name": "อาจารย์ สมชาย"})
    assert contact.status_code == 201
    contact_id = contact.json()["id"]
    for kind, value in [("line_user_id", "U123"), ("line_group_id", "G123"), ("email", "Teacher@TU.ac.th"), ("phone", "0812345678")]:
        assert client.post(f"/customers/contacts/{contact_id}/channels", json={"channel_type": kind, "value": value}).status_code == 201
        assert client.get("/customers/organizations", params={"q": value.lower() if kind == "email" else value}).json()[0]["id"] == org_id
    assert len(client.get(f"/customers/contacts/{contact_id}").json()["channels"]) == 4
    assert client.get("/customers/contacts", params={"q": "สมชาย"}).json()[0]["id"] == contact_id
    assert client.get("/customers/organizations", params={"q": "มหาวิทยาลัย"}).json()[0]["id"] == org_id
    assert client.post(f"/customers/contacts/{contact_id}/channels", json={"channel_type": "email", "value": "teacher@tu.ac.th"}).status_code == 409
    assert client.get("/customers/contacts", params={"q": "%"}).json() == []
    assert client.get("/customers/contacts", params={"q": "_"}).json() == []
    other = client.post(f"/customers/organizations/{org_id}/contacts", json={"name": "Other"}).json()["id"]
    assert client.post(f"/customers/contacts/{other}/channels", json={"channel_type": "line_group_id", "value": "G123"}).status_code == 201
    channel_id = client.get(f"/customers/contacts/{contact_id}").json()["channels"][0]["id"]
    assert client.delete(f"/customers/contacts/{other}/channels/{channel_id}").status_code == 404
    assert client.delete(f"/customers/contacts/{contact_id}/channels/{channel_id}").status_code == 204
    assert client.put(f"/customers/contacts/{contact_id}", json={"name": "Updated", "is_active": False}).json()["is_active"] is False


def test_validation_and_authorization(api):
    client, app = api
    assert client.post("/customers/organizations", json={"name": "   "}).status_code == 422
    assert client.post("/customers/organizations/999/contacts", json={"name": "Missing"}).status_code == 404
    assert client.post("/customers/contacts/999/channels", json={"channel_type": "invalid", "value": "x"}).status_code == 422
    assert client.get("/customers/organizations?limit=101").status_code == 422
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role=SimpleNamespace(name="Auditor"))
    assert client.get("/customers/organizations").status_code == 200
    assert client.post("/customers/organizations", json={"name": "Denied"}).status_code == 403
    app.dependency_overrides.pop(get_current_user)
    assert client.get("/customers/organizations").status_code == 401


def test_migration_upgrade_and_downgrade():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/cusprd01_customer_registry.py"
    spec = importlib.util.spec_from_file_location("customer_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        assert set(inspect(connection).get_table_names()) == {"organization", "contact", "channel_identity"}
        migration.downgrade()
        assert inspect(connection).get_table_names() == []
    engine.dispose()
