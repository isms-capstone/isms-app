import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from app.api.deps import require_admin, require_any_authenticated
from app.db.session import get_db

from app.api.v1.endpoints.master_data import router, selection_router  # noqa: E402
from app.db.base_class import Base  # noqa: E402
from app.db.models.master_data import Module, ProblemType, Product  # noqa: E402


def make_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    product = Product(name="ExamPlus")
    db.add(product)
    db.flush()
    module = Module(product_id=product.id, name="Login")
    db.add(module)
    db.flush()
    problem_type = ProblemType(module_id=module.id, name="Unable to sign in")
    db.add(problem_type)
    db.commit()
    ids = (product.id, module.id, problem_type.id)
    db.close()

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.include_router(selection_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: SessionLocal()
    app.dependency_overrides[require_admin] = lambda: object()
    app.dependency_overrides[require_any_authenticated] = lambda: object()
    return TestClient(app), ids


def test_case_template_and_canned_message_crud():
    client, (product_id, module_id, problem_type_id) = make_client()

    response = client.post(
        "/api/v1/admin/master-data/case-templates",
        json={
            "name": "Login Problem",
            "description": "Prefill login support cases",
            "product_id": product_id,
            "module_id": module_id,
            "problem_type_id": problem_type_id,
            "default_severity": "S2",
        },
    )
    assert response.status_code == 201
    template_id = response.json()["id"]

    response = client.get("/api/v1/master-data/case-templates")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Login Problem"

    response = client.patch(
        f"/api/v1/admin/master-data/case-templates/{template_id}",
        json={"default_severity": "S1"},
    )
    assert response.status_code == 200
    assert response.json()["default_severity"] == "S1"

    response = client.post(
        "/api/v1/admin/master-data/canned-messages",
        json={
            "name": "Initial Response",
            "message": "Hello, we received your case and are investigating.",
            "description": "Initial acknowledgement",
        },
    )
    assert response.status_code == 201
    message_id = response.json()["id"]

    response = client.get("/api/v1/master-data/canned-messages")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Initial Response"

    response = client.patch(
        f"/api/v1/admin/master-data/canned-messages/{message_id}",
        json={"message": "Hello, we received your case."},
    )
    assert response.status_code == 200

    response = client.delete(f"/api/v1/admin/master-data/case-templates/{template_id}")
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    response = client.delete(f"/api/v1/admin/master-data/canned-messages/{message_id}")
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    assert client.get("/api/v1/master-data/case-templates").json() == []
    assert client.get("/api/v1/master-data/canned-messages").json() == []


def test_case_template_rejects_mismatched_category_hierarchy():
    client, (product_id, module_id, problem_type_id) = make_client()
    bad_product = client.post(
        "/api/v1/admin/master-data/products",
        json={"name": "Get A"},
    )
    assert bad_product.status_code == 201

    response = client.post(
        "/api/v1/admin/master-data/case-templates",
        json={
            "name": "Bad Template",
            "product_id": bad_product.json()["id"],
            "module_id": module_id,
            "problem_type_id": problem_type_id,
            "default_severity": "S3",
        },
    )
    assert response.status_code == 422
