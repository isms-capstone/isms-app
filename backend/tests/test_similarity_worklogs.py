"""Regression tests for SIM decisions and internal/external communication boundaries."""

import os
from datetime import UTC, datetime
from threading import Event
from time import perf_counter
from types import SimpleNamespace

import pytest
from app.api.deps import get_current_user
from app.api.v1.endpoints import tickets as endpoints
from app.db.models.similarity_feedback import SimilarityFeedback
from app.db.models.ticket import Ticket
from app.db.models.ticket_link import TicketLink
from app.db.models.work_category import TicketAudit
from app.services import similarity
from app.services.external_communication import external_replies
from sqlalchemy import select

pytest_plugins = ["test_tickets"]

QUERY = "ระบบสอบแสดงข้อผิดพลาดเข้าสู่ระบบไม่ได้"


@pytest.mark.parametrize(
    "status",
    [
        "DRAFT",
        "NEW",
        "IN_PROGRESS",
        "PENDING_CUSTOMER",
        "PENDING_EXTERNAL",
        "REOPENED",
        "RESOLVED",
        "CLOSED",
        "CANCELLED",
        "DUPLICATE",
    ],
)
def test_search_again_through_case_lifecycle(capture, status):
    client, _, factory, data, _ = capture
    target = seed_case(factory, data, status=status, description=None)
    source = seed_case(factory, data)
    result = search(client, data, ticket_id=target)
    assert target not in [item["id"] for item in result["items"]]
    assert source in [item["id"] for item in result["items"]]
    response = client.post(
        f"/api/v1/tickets/similarity-feedback/{result['feedback_id']}",
        json={"decision": "new", "ticket_id": target},
    )
    assert response.status_code == 200, response.text
    with factory() as db:
        assert db.get(Ticket, target).status == status


def test_sources_can_be_extended_without_rewriting_ticket_query(capture, monkeypatch):
    _, _, factory, _, _ = capture

    def provider(db, **kwargs):
        return [
            {
                "id": 1,
                "source_type": "known_issue",
                "score": 88,
                "last_activity": "2026-11-05T00:00:00+00:00",
            }
        ]

    monkeypatch.setattr(similarity, "SEARCH_SOURCES", (provider,))
    with factory() as db:
        assert similarity.similar_cases(db, QUERY)[0]["source_type"] == "known_issue"


def test_same_customer_product_wins_even_when_display_scores_reach_100(capture):
    client, _, factory, data, other = capture
    preferred = seed_case(factory, data)
    seed_case(
        factory,
        data,
        organization_id=other,
        contact_id=None,
        product_instance_id=None,
        module_id=None,
        category_id=None,
    )
    result = search(client, data)
    assert result["items"][0]["id"] == preferred
    assert all(
        0 <= item["score"] <= 100 and "_rank" not in item for item in result["items"]
    )


@pytest.mark.skipif(
    os.getenv("REGISTRY_MARIADB_QA") != "1",
    reason="Full-text load QA requires disposable MariaDB",
)
def test_mariadb_fulltext_with_1000_cases(capture):
    from sqlalchemy import insert

    client, _, factory, data, _ = capture
    source = seed_case(factory, data)
    with factory() as db:
        row = db.get(Ticket, source)
        values = {
            column.name: getattr(row, column.name)
            for column in Ticket.__table__.columns
            if column.name not in {"id", "ticket_no"}
        }
        db.execute(
            insert(Ticket),
            [values | {"subject": QUERY + f" load {index}"} for index in range(1000)],
        )
        db.commit()
    started = perf_counter()
    result = search(client, data)
    assert result["available"] and len(result["items"]) == 5
    assert perf_counter() - started < 1.6


def seed_case(factory, context, **overrides):
    with factory() as db:
        from app.db.models.user import User

        user_id = db.scalar(select(User.id).limit(1))
        values = dict(
            context,
            subject=QUERY,
            description="รายละเอียดปัญหาการสอบ",
            status="CLOSED",
            channel="phone",
            created_by_id=user_id,
            owner_id=user_id,
            created_at=datetime.now(UTC).replace(tzinfo=None),
            reported_at=datetime.now(UTC).replace(tzinfo=None),
            severity="S2",
            impact_scope="organization",
            is_exam_window=False,
            resolution_detail="ออกจากระบบและเข้าสู่ระบบใหม่",
        )
        values.update(overrides)
        row = Ticket(**values)
        db.add(row)
        db.commit()
        return row.id


def search(client, context, **extra):
    response = client.get(
        "/api/v1/tickets/similar",
        params={
            "q": QUERY,
            "organization_id": context["organization_id"],
            "product_instance_id": context["product_instance_id"],
            **extra,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_search_metadata_limit_open_closed_and_feedback(capture):
    client, _, factory, data, _ = capture
    for index in range(7):
        seed_case(factory, data, status="CLOSED" if index % 2 else "IN_PROGRESS")
    seed_case(factory, data, status="DRAFT")
    result = search(client, data)
    assert len(result["items"]) == 5
    assert result["decision_required"] and result["available"]
    assert {item["status"] for item in result["items"]} == {"CLOSED", "IN_PROGRESS"}
    assert all(
        item["source_type"] == "ticket"
        and item["last_activity"].endswith("+00:00")
        and item["assignee"] is None
        for item in result["items"]
    )
    assert [item["score"] for item in result["items"]] == sorted(
        [item["score"] for item in result["items"]], reverse=True
    )
    with factory() as db:
        feedback = db.get(SimilarityFeedback, result["feedback_id"])
        assert len(feedback.suggested) == 5 and feedback.query == QUERY


def test_create_requires_confirmed_decision_and_attaches_feedback(capture):
    client, _, factory, data, _ = capture
    seed_case(factory, data)
    payload = dict(data, subject=QUERY, channel="phone")
    assert client.post("/api/v1/tickets", json=payload).status_code == 409
    result = search(client, data)
    fid = result["feedback_id"]
    assert (
        client.post(
            "/api/v1/tickets", json=payload | {"similarity_feedback_id": fid}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/tickets/similarity-feedback/{fid}", json={"decision": "new"}
        ).status_code
        == 200
    )
    response = client.post(
        "/api/v1/tickets", json=payload | {"similarity_feedback_id": fid}
    )
    assert response.status_code == 201, response.text
    with factory() as db:
        assert db.get(SimilarityFeedback, fid).ticket_id == response.json()["id"]
    assert (
        client.post(
            "/api/v1/tickets", json=payload | {"similarity_feedback_id": fid}
        ).status_code
        == 409
    )


def test_stale_feedback_is_rejected(capture):
    client, _, factory, data, _ = capture
    seed_case(factory, data)
    fid = search(client, data)["feedback_id"]
    client.post(f"/api/v1/tickets/similarity-feedback/{fid}", json={"decision": "new"})
    result = client.post(
        "/api/v1/tickets",
        json=dict(
            data,
            subject=QUERY + "เปลี่ยนแล้ว",
            channel="phone",
            similarity_feedback_id=fid,
        ),
    )
    assert result.status_code == 409


def test_reuse_maps_destination_customer_and_saves_editable_fields(capture):
    client, _, factory, data, other = capture
    from app.db.models.product import ProductInstance

    with factory() as db:
        product_id = db.get(ProductInstance, data["product_instance_id"]).product_id
    response = client.post(
        f"/api/v1/organizations/{other}/products/{product_id}/instances",
        json={
            "code": "other-prod",
            "name": "Other customer instance",
            "version": "1",
            "environment": "production",
            "url": "https://example.org",
        },
    )
    assert response.status_code == 201, response.text
    other_instance = response.json()["id"]
    source_id = seed_case(
        factory,
        data,
        organization_id=other,
        contact_id=None,
        product_instance_id=other_instance,
    )
    fid = search(client, data)["feedback_id"]
    reused = {
        "product_instance_id": other_instance,
        "module_id": data["module_id"],
        "category_id": data["category_id"],
        "severity": "S3",
        "impact_scope": "single_user",
        "is_exam_window": False,
        "resolution_detail": "ผู้ใช้แก้ไขวิธีแก้เดิม",
    }
    path = f"/api/v1/tickets/similarity-feedback/{fid}"
    assert (
        client.post(
            path,
            json={
                "decision": "reuse",
                "chosen_ticket_id": source_id,
                "reuse_values": reused,
            },
        ).status_code
        == 422
    )
    reused["product_instance_id"] = data["product_instance_id"]
    assert (
        client.post(
            path,
            json={
                "decision": "reuse",
                "chosen_ticket_id": source_id,
                "reuse_values": reused,
            },
        ).status_code
        == 200
    )
    response = client.post(
        "/api/v1/tickets",
        json=dict(data, subject=QUERY, channel="phone", similarity_feedback_id=fid)
        | reused,
    )
    assert response.status_code == 201, response.text
    assert response.json()["severity"] == "S3"
    assert response.json()["resolution_detail"] == reused["resolution_detail"]


def test_link_creates_real_relation_and_audit_without_changing_status(capture):
    client, _, factory, data, _ = capture
    source_id = seed_case(factory, data)
    fid = search(client, data)["feedback_id"]
    assert (
        client.post(
            f"/api/v1/tickets/similarity-feedback/{fid}",
            json={"decision": "link", "chosen_ticket_id": source_id},
        ).status_code
        == 200
    )
    response = client.post(
        "/api/v1/tickets",
        json=dict(data, subject=QUERY, channel="phone", similarity_feedback_id=fid),
    )
    assert response.status_code == 201, response.text
    target_id = response.json()["id"]
    with factory() as db:
        a, b = sorted((source_id, target_id))
        link = db.scalar(
            select(TicketLink).where(
                TicketLink.ticket_id == a, TicketLink.related_ticket_id == b
            )
        )
        assert {link.ticket_id, link.related_ticket_id} == {source_id, target_id}
        assert db.get(Ticket, source_id).status == "CLOSED"
        assert db.get(Ticket, target_id).status == "NEW"
        log = db.scalar(
            select(TicketAudit).where(
                TicketAudit.ticket_id == target_id,
                TicketAudit.event == "similarity_decision",
            )
        )
        assert (
            log.changes["decision"] == "link"
            and log.actor_id == response.json()["created_by_id"]
        )


def test_repeat_search_excludes_current_and_existing_case_decision_is_attached(capture):
    client, _, factory, data, _ = capture
    target = seed_case(factory, data, description=None, status="IN_PROGRESS")
    source = seed_case(factory, data)
    result = search(client, data, ticket_id=target)
    assert source in [item["id"] for item in result["items"]]
    assert target not in [item["id"] for item in result["items"]]
    fid = result["feedback_id"]
    response = client.post(
        f"/api/v1/tickets/similarity-feedback/{fid}",
        json={"decision": "link", "chosen_ticket_id": source, "ticket_id": target},
    )
    assert response.status_code == 200, response.text
    with factory() as db:
        assert db.get(SimilarityFeedback, fid).ticket_id == target


def test_feedback_cannot_be_used_by_another_user(capture):
    client, app, factory, data, _ = capture
    seed_case(factory, data)
    fid = search(client, data)["feedback_id"]
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=99999, role=SimpleNamespace(name="Admin")
    )
    assert (
        client.post(
            f"/api/v1/tickets/similarity-feedback/{fid}", json={"decision": "new"}
        ).status_code
        == 403
    )


def test_draft_publication_cannot_bypass_similarity(capture):
    client, _, factory, data, _ = capture
    seed_case(factory, data)
    response = client.post(
        "/api/v1/tickets",
        json=dict(data, subject=QUERY, channel="phone", save_as_draft=True),
    )
    assert response.status_code == 201
    tid = response.json()["id"]
    assert (
        client.patch(
            f"/api/v1/tickets/{tid}/status", json={"status": "NEW"}
        ).status_code
        == 409
    )
    result = search(client, data, ticket_id=tid)
    response = client.post(
        f"/api/v1/tickets/similarity-feedback/{result['feedback_id']}",
        json={"decision": "new", "ticket_id": tid},
    )
    assert response.status_code == 200, response.text
    assert (
        client.patch(
            f"/api/v1/tickets/{tid}/status", json={"status": "NEW"}
        ).status_code
        == 200
    )


def test_timeout_failopen_and_bounded_wait(capture, monkeypatch):
    client, _, factory, data, _ = capture
    seed_case(factory, data)
    monkeypatch.setattr(endpoints, "search_with_deadline", lambda *args, **kwargs: None)
    assert not search(client, data)["available"]
    assert (
        client.post(
            "/api/v1/tickets", json=dict(data, subject=QUERY, channel="phone")
        ).status_code
        == 201
    )
    done = Event()

    def slow(*args, **kwargs):
        try:
            Event().wait(0.1)
            return []
        finally:
            done.set()

    monkeypatch.setattr(similarity, "similar_cases", slow)
    monkeypatch.setattr(similarity, "SEARCH_TIMEOUT", 0.01)
    with factory() as db:
        started = perf_counter()
        assert similarity.search_with_deadline(db.get_bind(), q=QUERY) is None
        assert perf_counter() - started < 0.08
    assert done.wait(1)


def test_timed_out_reader_cannot_rollback_the_case_number_transaction(
    capture, monkeypatch
):
    from app.db.models.ticket import TicketNumberSequence
    from sqlalchemy.orm import Session

    _client, _, factory, data, _ = capture
    seed_case(factory, data)
    release, finished = Event(), Event()

    class ReaderSession(Session):
        def __exit__(self, *args):
            try:
                return super().__exit__(*args)
            finally:
                finished.set()

    def slow(db, **kwargs):
        db.scalar(select(Ticket.id).limit(1))
        release.wait(2)
        return []

    monkeypatch.setattr(similarity, "Session", ReaderSession)
    monkeypatch.setattr(similarity, "similar_cases", slow)
    monkeypatch.setattr(similarity, "SEARCH_TIMEOUT", 0.01)
    with factory() as db:
        baseline = db.get(TicketNumberSequence, "209911")
        previous = baseline.value if baseline else 0
        assert similarity.search_with_deadline(db.get_bind(), q=QUERY) is None
        try:
            number = endpoints.next_ticket_number(db, datetime(2099, 11, 1))
            release.set()
            assert finished.wait(2)
            db.commit()
        finally:
            release.set()
    with factory() as db:
        assert db.get(TicketNumberSequence, "209911").value == previous + 1
        assert number.endswith(f"{previous + 1:05d}")


@pytest.mark.parametrize("channel", ["portal", "line", "email"])
def test_internal_notes_never_enter_external_payloads_and_audit_is_atomic(
    capture, channel
):
    client, app, factory, data, _ = capture
    ticket_id = seed_case(factory, data)
    path = f"/api/v1/tickets/{ticket_id}"
    response = client.post(
        path + "/worklogs",
        json={"kind": "internal_note", "body": "SECRET TEAM NOTE"},
    )
    assert response.status_code == 201, response.text
    note = response.json()
    assert (
        client.post(
            path + "/worklogs",
            json={
                "kind": "internal_note",
                "body": "secret",
                "channel": "line_oa" if channel == "line" else channel,
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            path + "/worklogs",
            json={
                "kind": "public_reply",
                "body": "Customer reply",
                "channel": "line_oa" if channel == "line" else channel,
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            path + "/worklogs",
            json={
                "kind": "public_reply",
                "body": "   ",
                "channel": "line_oa" if channel == "line" else channel,
            },
        ).status_code
        == 422
    )
    response = client.get(path + f"/external-replies/{channel}")
    assert response.status_code == 200
    assert [row["body"] for row in response.json()] == ["Customer reply"]
    assert "SECRET" not in response.text and "actor_id" not in response.text
    with factory() as db:
        assert all(
            "SECRET" not in str(external_replies(db, ticket_id, c))
            for c in ["portal", "line", "email"]
        )
        logs = db.scalars(
            select(TicketAudit).where(TicketAudit.ticket_id == ticket_id)
        ).all()
        assert len(logs) == 2
        assert logs[0].actor_id == note["actor_id"]
        assert logs[0].created_at == datetime.fromisoformat(note["created_at"]).replace(
            tzinfo=None
        )
        assert logs[0].changes["kind"] == "internal_note"
        assert logs[1].changes["kind"] == "public_reply"
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=note["actor_id"], role=SimpleNamespace(name="Customer")
    )
    assert client.get(path + "/worklogs").status_code == 403
    assert client.get(path + "/history").status_code == 403
    assert client.get(path + f"/external-replies/{channel}").status_code == 403
