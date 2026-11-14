from base64 import b64decode
from datetime import datetime, timezone
import json
from uuid import uuid4

from jose import jwt
from sqlalchemy import select

from app.db.models.portal import PortalEmail
from app.db.models.product import ProductInstance
from app.db.models.ticket import Ticket
from app.db.models.work_category import TicketWorklog
from test_tickets import capture  # noqa: F401


def test_product_grant_intake_and_reply_scope(capture, monkeypatch, tmp_path):
    client, app, factory, context, other_org = capture
    with factory() as db:
        instance = db.get(ProductInstance, context["product_instance_id"])
        product_id = instance.product_id
    from app.api.deps import get_current_user
    actor = app.dependency_overrides[get_current_user]().id
    secret = "test-only-" * 5
    monkeypatch.setenv("POR_PRODUCTS", json.dumps({"exam": {
        "secret": secret, "product_id": product_id, "intake_user_id": actor,
        "origins": ["https://exam.example"],
    }}))
    now = int(datetime.now(timezone.utc).timestamp())

    def grant(**changes):
        claims = dict(iss="exam", aud="isms-portal", sub="external-user", jti=uuid4().hex,
                      iat=now, exp=now + 300, organization_id=context["organization_id"],
                      instance_id=context["product_instance_id"], module_id=context["module_id"],
                      name="Customer", email="customer@example.org",
                      source_url="https://exam.example/screen?private=1", exam_or_course_context="EX-42")
        return jwt.encode(claims | changes, secret, algorithm="HS256")

    base = "/api/v1/portal"
    assert client.post(base + "/sso-entry", data={"token": grant(exp=now-1)}).status_code == 401
    assert client.post(base + "/sso-entry", data={"token": grant(organization_id=other_org)}).status_code == 401
    token = grant()
    assert client.post(base + "/sso-entry", data={"token": token}).status_code == 200
    payload = {"token": token, "subject": "Exam problem"}
    png = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a2ZkAAAAASUVORK5CYII=")
    monkeypatch.setattr("app.api.v1.endpoints.tickets.ATTACHMENT_DIR", tmp_path)
    created = client.post(base + "/cases", data=payload,
                          files={"screenshot": ("capture.png", png, "image/png")})
    assert created.status_code == 201, created.text
    assert client.post(base + "/cases", data=payload).json() == created.json()
    with factory() as db:
        ticket = db.scalar(select(Ticket).where(Ticket.ticket_no == created.json()["ticket_no"]))
        assert ticket.source_url == "https://exam.example/screen"
        assert ticket.exam_or_course_context == "EX-42"
        ticket_id = ticket.id
        db.add(TicketWorklog(ticket_id=ticket.id, actor_id=actor, kind="internal_note",
                             is_internal=True, body="Staff only"))
        db.commit()
    assert [file.read_bytes() for file in tmp_path.glob("*.png")] == [png]
    reply = client.post(f"/api/v1/tickets/{ticket_id}/worklogs", json={
        "kind": "public_reply", "channel": "portal", "body": "Visible",
    })
    assert reply.status_code == 201, reply.text
    with factory() as db:
        assert db.get(PortalEmail, reply.json()["id"]).recipient == "customer@example.org"
    assert [r["body"] for r in client.post(base + "/status", data={"token": token}).json()[0]["replies"]] == ["Visible"]
    assert client.post(base + "/status", data={"token": grant(sub="someone-else")}).json() == []
