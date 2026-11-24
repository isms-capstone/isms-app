"""Self-service portal (POR-07..10): sign-in link, visibility, intake, notices."""
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.models.portal import PortalMagicLink, PortalOutbox
from app.db.models.sla import SlaClock
from app.db.models.ticket import Ticket
from app.services import portal_access
from test_tickets import capture  # noqa: F401

BASE = "/api/v1/portal"


def sign_in(client, email):
    sent = client.post(f"{BASE}/magic-link", json={"email": email})
    assert sent.status_code == 202, sent.text
    link = sent.json()["dev_links"][0]
    token = link.split("token=", 1)[1]
    session = client.post(f"{BASE}/magic-link/verify", json={"token": token})
    assert session.status_code == 200, session.text
    # A link works only once.
    assert client.post(f"{BASE}/magic-link/verify", json={"token": token}).status_code == 401
    return {"X-Portal-Session": session.json()["session"]}, token


def test_portal_sign_in_visibility_intake_and_replies(capture):
    client, _, factory, data, _ = capture
    org, contact_id = data["organization_id"], data["contact_id"]
    assert client.post(f"/api/v1/customers/contacts/{contact_id}/channels",
                       json={"channel_type": "email", "value": "teacher@example.org"}).status_code == 201
    colleague = client.post(f"/api/v1/customers/organizations/{org}/contacts", json={"name": "Coordinator"}).json()
    assert client.post(f"/api/v1/customers/contacts/{colleague['id']}/channels",
                       json={"channel_type": "email", "value": "coord@example.org"}).status_code == 201

    # Unknown addresses get the same answer and no link (no customer enumeration).
    unknown = client.post(f"{BASE}/magic-link", json={"email": "nobody@example.org"})
    assert unknown.status_code == 202 and unknown.json()["dev_links"] == []

    teacher, _ = sign_in(client, "teacher@example.org")
    with factory() as db:
        assert db.scalar(select(PortalOutbox.id).where(PortalOutbox.recipient == "teacher@example.org"))
    me = client.get(f"{BASE}/me", headers=teacher).json()
    assert me["scope"] == "own" and me["systems"][0]["id"] == data["product_instance_id"]

    created = client.post(f"{BASE}/me/cases", headers=teacher, data={
        "subject": "ส่งคำตอบไม่สำเร็จ", "description": "กดส่งแล้วค้าง",
        "product_instance_id": str(data["product_instance_id"])})
    assert created.status_code == 201, created.text
    number = created.json()["ticket_no"]
    with factory() as db:
        ticket = db.scalar(select(Ticket).where(Ticket.ticket_no == number))
        assert ticket.channel == "portal" and ticket.contact_id == contact_id
        assert ticket.severity == "S3" and ticket.current_tier == 2
        assert db.scalar(select(SlaClock.id).where(SlaClock.ticket_id == ticket.id))
        ticket_id = ticket.id

    # Staff answer: the public portal reply is visible, the internal note is not (WRK-03).
    assert client.post(f"/api/v1/tickets/{ticket_id}/worklogs", json={
        "kind": "internal_note", "body": "Check server logs"}).status_code == 201
    assert client.post(f"/api/v1/tickets/{ticket_id}/worklogs", json={
        "kind": "public_reply", "channel": "portal", "body": "แก้ไขแล้ว กรุณาลองใหม่"}).status_code == 201
    detail = client.get(f"{BASE}/me/cases/{number}", headers=teacher).json()
    assert [reply["body"] for reply in detail["replies"]] == ["แก้ไขแล้ว กรุณาลองใหม่"]
    assert "Check server logs" not in str(detail)
    assert client.get(f"{BASE}/me/cases", headers=teacher).json()[0]["replies"] == 1

    # POR-08: a normal contact sees only their own cases; a coordinator sees the organisation's.
    coordinator, _ = sign_in(client, "coord@example.org")
    assert client.get(f"{BASE}/me/cases", headers=coordinator).json() == []
    assert client.get(f"{BASE}/me/cases/{number}", headers=coordinator).status_code == 404
    assert client.put(f"{BASE}/contacts/{colleague['id']}/scope", json={"scope": "organization"}).status_code == 200
    assert number in [row["ticket_no"] for row in client.get(f"{BASE}/me/cases", headers=coordinator).json()]

    # A case of another organisation's system cannot be opened from this session.
    other_system = client.post(f"{BASE}/me/cases", headers=teacher, data={
        "subject": "x", "product_instance_id": "999999"})
    assert other_system.status_code == 422


def test_portal_sessions_are_not_staff_tokens(capture):
    client, _, factory, data, _ = capture
    with factory() as db:
        staff = create_access_token("someone")
        with pytest.raises(HTTPException):
            portal_access.contact_from_session(db, staff)
        from app.db.models.customer import Contact
        session = portal_access.issue_session(db.get(Contact, data["contact_id"]))
        with pytest.raises(HTTPException):
            get_current_user(db, session)
    assert client.get(f"{BASE}/me").status_code == 401
    assert client.get(f"{BASE}/me", headers={"X-Portal-Session": "garbage"}).status_code == 401


def test_expired_link_is_rejected(capture):
    client, _, factory, data, _ = capture
    client.post(f"/api/v1/customers/contacts/{data['contact_id']}/channels",
                json={"channel_type": "email", "value": "late@example.org"})
    token = client.post(f"{BASE}/magic-link", json={"email": "late@example.org"}).json()["dev_links"][0].split("token=")[1]
    with factory() as db:
        row = db.scalar(select(PortalMagicLink).where(PortalMagicLink.email == "late@example.org"))
        row.expires_at = row.created_at - timedelta(minutes=1)
        db.commit()
    assert client.post(f"{BASE}/magic-link/verify", json={"token": token}).status_code == 401


def test_status_notice_follows_master_incident(capture):
    client, _, _, data, _ = capture
    master = client.post("/api/v1/tickets", json=dict(data, subject="ExamPlus down", channel="phone")).json()
    notice = client.post(f"{BASE}/announcements", json={
        "title": "ExamPlus เข้าระบบไม่ได้", "message": "ทีมกำลังแก้ไข", "ticket_no": master["ticket_no"]})
    assert notice.status_code == 201, notice.text
    assert [row["title"] for row in client.get(f"{BASE}/announcements").json()] == ["ExamPlus เข้าระบบไม่ได้"]
    assert client.post(f"{BASE}/announcements", json={
        "title": "x", "message": "y", "ticket_no": "DVHT-000000-00000"}).status_code == 422
    assert client.post(f"{BASE}/announcements/{notice.json()['id']}/resolve").status_code == 200
    assert client.get(f"{BASE}/announcements").json() == []


def test_worker_delivers_replies_and_sign_in_links(capture, monkeypatch):
    client, _, factory, data, _ = capture
    from app.services import portal_mail

    client.post(f"/api/v1/customers/contacts/{data['contact_id']}/channels",
                json={"channel_type": "email", "value": "mail@example.org"})
    headers, _ = sign_in(client, "mail@example.org")
    number = client.post(f"{BASE}/me/cases", headers=headers, data={
        "subject": "Need help", "product_instance_id": str(data["product_instance_id"])}).json()["ticket_no"]
    with factory() as db:
        ticket_id = db.scalar(select(Ticket.id).where(Ticket.ticket_no == number))
    client.post(f"/api/v1/tickets/{ticket_id}/worklogs",
                json={"kind": "public_reply", "channel": "portal", "body": "Done"})
    sent = []

    class FakeSMTP:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def starttls(self, context=None): sent.append("starttls")
        def send_message(self, message): sent.append((message["To"], message["Subject"], message.get_content()))

    monkeypatch.setenv("POR_SMTP_HOST", "smtp.example.org")
    monkeypatch.setenv("POR_SMTP_FROM", "support@example.org")
    monkeypatch.setattr(portal_mail.smtplib, "SMTP", FakeSMTP)
    with factory() as db:
        assert portal_mail.deliver_replies(db) == 2
        assert portal_mail.deliver_replies(db) == 0  # queues are empty afterwards
    reply = next(item for item in sent if isinstance(item, tuple) and number in item[1])
    assert f"/portal/cases/{number}" in reply[2] and "Done" not in reply[2]  # no reply body in e-mail
