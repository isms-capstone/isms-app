import importlib.util
from pathlib import Path
from types import SimpleNamespace

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from app.api.deps import get_current_user
from test_customers import api  # Shared isolated DB and authenticated client.


def role(app, name):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role=SimpleNamespace(name=name))


def instance_body(**changes):
    return {"code": "production", "name": "TU installation", "version": "1.2.3",
            "environment": "production", "url": "https://exam.example.org", **changes}


def test_extensible_catalogue_and_product_scoped_modules(api):
    client, app = api
    role(app, "Admin")
    ids = []
    for code, name in [("ExamPlus", "ExamPlus"), ("geta", "GetA"),
                       ("logbook", "Logbook"), ("future_service", "บริการใหม่")]:
        result = client.post("/products", json={"code": code, "name": name})
        assert result.status_code == 201, result.text
        ids.append(result.json()["id"])
    exam, geta, _, _ = ids
    assert client.get("/products", params={"q": "บริการ"}).json()[0]["code"] == "future_service"
    assert client.post("/products", json={"code": " EXAMPLUS ", "name": "Duplicate"}).status_code == 409
    for code, name in [("teacher", "Teacher"), ("proctor", "Proctor"),
                       ("student-web", "Student (Web)"), ("student-app", "Student (App)")]:
        assert client.post(f"/products/{exam}/modules", json={"code": code, "name": name}).status_code == 201
    teacher = client.get(f"/products/{exam}/modules").json()[0]
    assert len(client.get(f"/products/{exam}").json()["modules"]) == 4
    assert client.post(f"/products/{exam}/modules", json={"code": "teacher", "name": "Duplicate"}).status_code == 409
    assert client.post(f"/products/{geta}/modules", json={"code": "teacher", "name": "GetA Teacher"}).status_code == 201
    assert len(client.get(f"/products/{geta}/modules").json()) == 1
    assert client.put(f"/products/{geta}/modules/{teacher['id']}", json={"code": teacher["code"], "name": "Wrong product"}).status_code == 404
    assert client.put(f"/products/{exam}", json={"code": "examplus", "name": "ExamPlus", "is_active": False}).status_code == 200
    assert len(client.get("/products?is_active=true").json()) == 3
    assert len(client.get("/products?offset=1&limit=1").json()) == 1


def test_customer_instances_and_reference_integrity(api):
    client, app = api
    role(app, "Admin")
    product_id = client.post("/products", json={"code": "examplus", "name": "ExamPlus"}).json()["id"]
    org1 = client.post("/customers/organizations", json={"name": "TU"}).json()["id"]
    org2 = client.post("/customers/organizations", json={"name": "CU"}).json()["id"]
    role(app, "Agent")
    path = f"/organizations/{org1}/products/{product_id}/instances"
    created = client.post(path, json=instance_body())
    assert created.status_code == 201, created.text
    instance_id = created.json()["id"]
    assert created.json()["url"] == "https://exam.example.org/"
    assert client.post(path, json=instance_body()).status_code == 409
    assert client.post(path, json=instance_body(code="staging", environment="staging")).status_code == 201
    assert client.post(f"/organizations/{org2}/products/{product_id}/instances", json=instance_body()).status_code == 201
    result = client.get("/product-instances", params={"organization_id": org1, "product_id": product_id})
    assert len(result.json()) == 2
    assert all(row["organization_id"] == org1 for row in result.json())
    updated = client.put(f"/product-instances/{instance_id}", json=instance_body(version="2.0", is_active=False))
    assert updated.status_code == 200
    assert updated.json()["version"] == "2.0"
    assert updated.json()["organization_id"] == org1
    assert len(client.get("/product-instances", params={"organization_id": org1, "is_active": True}).json()) == 1
    assert client.put(f"/product-instances/{instance_id}", json=instance_body(code="staging")).status_code == 409
    assert client.get(f"/product-instances/{instance_id}").json()["version"] == "2.0"
    assert client.post(f"/organizations/999/products/{product_id}/instances", json=instance_body()).status_code == 404
    assert client.post(f"/organizations/{org1}/products/999/instances", json=instance_body()).status_code == 404
    assert client.get("/product-instances?organization_id=999").status_code == 404
    assert client.get("/products/999/modules").status_code == 404


def test_permissions_and_input_validation(api):
    client, app = api
    for name in ["Agent", "User", "Auditor", "Executive", "Team Lead"]:
        role(app, name)
        assert client.get("/products").status_code == 200
        assert client.post("/products", json={"code": "exam", "name": "Exam"}).status_code == 403
        assert client.post("/products/1/modules", json={"code": "teacher", "name": "Teacher"}).status_code == 403
    role(app, "Admin")
    assert client.post("/products", json={"code": "bad code", "name": "Invalid"}).status_code == 422
    assert client.post("/products", json={"code": "valid", "name": " "}).status_code == 422
    assert client.get("/products?limit=101").status_code == 422
    assert client.get("/products", params={"q": "%"}).json() == []
    for changes in [{"url": "javascript:alert(1)"}, {"url": "https://user:secret@example.org"},
                    {"version": " "}, {"organization_id": 3}, {"environment": " "}]:
        assert client.post("/organizations/1/products/1/instances", json=instance_body(**changes)).status_code == 422
    role(app, "Auditor")
    assert client.post("/organizations/1/products/1/instances", json=instance_body()).status_code == 403
    assert client.put("/product-instances/1", json=instance_body()).status_code == 403
    app.dependency_overrides.pop(get_current_user)
    assert client.get("/products").status_code == 401
    assert client.get("/product-instances").status_code == 401


def test_product_migration_preserves_customer_registry():
    directory = Path(__file__).resolve().parents[1] / "alembic/versions"
    migrations = []
    for filename in ["cusprd01_customer_registry.py", "cusprd02_product_registry.py"]:
        spec = importlib.util.spec_from_file_location(filename[:-3], directory / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        migrations.append(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        for migration in migrations:
            migration.op = operations
            migration.upgrade()
        assert set(inspect(connection).get_table_names()) == {
            "organization", "contact", "channel_identity", "product", "product_module", "product_instance"}
        assert len(inspect(connection).get_foreign_keys("product_instance")) == 2
        migrations[1].downgrade()
        assert set(inspect(connection).get_table_names()) == {"organization", "contact", "channel_identity"}
        migrations[1].upgrade()
        assert "product_instance" in inspect(connection).get_table_names()
    engine.dispose()
