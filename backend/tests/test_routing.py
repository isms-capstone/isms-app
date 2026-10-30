"""ESC-01..09 acceptance and transaction/security regression tests."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.api.deps import get_current_user
from app.db.models.master_data import BusinessCalendar, BusinessHoliday
from app.db.models.product import ProductInstance
from app.db.models.routing import (
    ProductTierRoute,
    RoutingEvent,
    RoutingJobLease,
    RoutingNotification,
    RoutingPolicy,
    TeamRouting,
    TierInterval,
)
from app.db.models.ticket import Ticket
from app.db.models.ticket_history import TicketStatusHistory
from app.db.models.user import Role, Team, User
from app.services.routing_jobs import run_routing_checks, within_business_hours
from sqlalchemy import delete, func, select
from test_tickets import capture  # noqa: F401 - register the shared pytest fixture


@pytest.fixture
def routing(request):
    client, app, factory, context, _ = request.getfixturevalue("capture")
    key = uuid4().hex[:8]
    with factory() as db:
        lease = db.get(RoutingJobLease, 1)
        if lease:
            lease.locked_until = datetime(1970, 1, 1)
        policy = db.get(RoutingPolicy, 1)
        if policy:
            policy.s1_minutes = 15
            policy.enabled = True
            policy.business_calendar_id = None
        admin = db.get(User, app.dependency_overrides[get_current_user]().id)
        teams = []
        for tier in (2, 1, 0):
            team = Team(name=f"ESC-{key}-{tier}")
            db.add(team)
            db.flush()
            teams.append(team)
        admin.team_id = teams[0].id
        ids = {"admin": admin.id}
        team_ids = [t.id for t in teams]
        for name, role_name, tier, index in [
            ("owner", "Agent", 2, 0),
            ("peer", "Agent", 2, 0),
            ("specialist", "Specialist", 1, 1),
            ("developer", "Developer", 0, 2),
            ("lead", "Team Lead", 2, 0),
            ("outsider", "Agent", 2, 1),
            ("auditor", "Executive", 2, 0),
        ]:
            role = db.scalar(select(Role).where(Role.name == role_name))
            if not role:
                role = Role(name=role_name)
                db.add(role)
                db.flush()
            u = User(
                username=f"{key}-{name}",
                email=f"{key}-{name}@example.org",
                role_id=role.id,
                hashed_password="unused",
                team_id=team_ids[index],
                default_tier=tier,
                is_available=True,
            )
            db.add(u)
            db.flush()
            ids[name] = u.id
        product = db.get(ProductInstance, context["product_instance_id"]).product_id
        for tier, team in zip((2, 1, 0), team_ids):
            db.add(ProductTierRoute(product_id=product, tier=tier, team_id=team))
        db.add(TeamRouting(team_id=team_ids[0], leader_id=ids["lead"]))
        db.commit()

    def login(name):
        def current():
            with factory() as db:
                u = db.get(User, ids[name])
                return SimpleNamespace(
                    id=u.id,
                    role=SimpleNamespace(name=u.role.name),
                    team_id=u.team_id,
                    default_tier=u.default_tier,
                    is_available=u.is_available,
                    is_active=u.is_active,
                    full_name=u.full_name,
                    username=u.username,
                )

        app.dependency_overrides[get_current_user] = current

    login("owner")

    def create(**changes):
        r = client.post(
            "/api/v1/tickets",
            json=context | {"subject": "ESC acceptance", "channel": "phone"},
        )
        assert r.status_code == 201, r.text
        with factory() as db:
            t = db.get(Ticket, r.json()["id"])
            t.assignee_id = ids["owner"]
            for k, v in changes.items():
                setattr(t, k, v)
            db.commit()
        return r.json()["id"]

    return SimpleNamespace(
        client=client,
        factory=factory,
        login=login,
        create=create,
        ids=ids,
        teams=team_ids,
        product=product,
        context=context,
    )


def post(r, case, action, **body):
    return r.client.post(f"/api/v1/tickets/{case}/{action}", json=body)


def state(r, case):
    response = r.client.get(f"/api/v1/tickets/{case}/routing")
    assert response.status_code == 200, response.text
    return response.json()


def handoff(r, case, **changes):
    body = {
        "expected_version": state(r, case)["version"],
        "tier": 1,
        "assignee_id": r.ids["specialist"],
        "reason": "Need diagnosis",
        "checked": "Checked logs",
        "requested": "Investigate fault",
    }
    body.update(changes)
    return post(r, case, "handoff", **body)


def test_esc_handoff_required_context_owner_timing_and_return(routing):
    r = routing
    case = r.create()
    before = r.client.get(f"/api/v1/tickets/{case}").json()
    for field in ("reason", "checked", "requested"):
        assert handoff(r, case, **{field: "   "}).status_code == 422
    assert not state(r, case)["events"]
    result = handoff(r, case)
    assert result.status_code == 200, result.text
    s = result.json()
    assert (
        s["tier"] == 1
        and s["owner"]["id"] == r.ids["owner"]
        and s["assignee"]["id"] == r.ids["specialist"]
    )
    assert (
        s["events"][0]["checked"] == "Checked logs"
        and s["events"][0]["requested"] == "Investigate fault"
    )
    assert (
        len(s["intervals"]) == 2
        and s["intervals"][0]["exited_at"]
        and s["intervals"][1]["status_history_id"]
    )
    assert handoff(r, case, expected_version=0).status_code == 409
    r.login("owner")
    assert (
        post(
            r,
            case,
            "return",
            expected_version=s["version"],
            event_id=s["events"][0]["id"],
            reason="Cannot return as owner",
        ).status_code
        == 403
    )
    r.login("specialist")
    assert (
        post(
            r,
            case,
            "return",
            expected_version=s["version"],
            event_id=s["events"][0]["id"],
            reason=" ",
        ).status_code
        == 422
    )
    response = post(
        r,
        case,
        "return",
        expected_version=s["version"],
        event_id=s["events"][0]["id"],
        reason="Clear browser cache",
    )
    assert response.status_code == 200, response.text
    returned = response.json()
    assert (
        returned["tier"] == 2
        and returned["assignee"]["id"] == r.ids["owner"]
        and returned["owner"] == s["owner"]
    )
    assert len(returned["intervals"]) == 3 and set(returned["seconds_by_tier"]) == {
        "2",
        "1",
        "0",
    }
    r.login("owner")
    assert (
        post(
            r,
            case,
            "return",
            expected_version=returned["version"],
            event_id=s["events"][0]["id"],
            reason="Again",
        ).status_code
        == 409
    )
    after = r.client.get(f"/api/v1/tickets/{case}").json()
    assert all(
        after[k] == before[k]
        for k in ("id", "ticket_no", "created_at", "owner_id", "status")
    )
    with r.factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Ticket)
                .where(Ticket.ticket_no == before["ticket_no"])
            )
            == 1
        )
        histories = [
            h
            for h in db.scalars(
                select(TicketStatusHistory).where(TicketStatusHistory.ticket_id == case)
            ).all()
            if h.details.get("operation") != "tier_entry"
        ]
        assert (
            len(histories) == 2
            and histories[0].details["requested"] == "Investigate fault"
        )


def test_esc_assignment_acl_stale_version_and_availability(routing):
    r = routing
    case = r.create(assignee_id=None)
    r.login("outsider")
    assert post(r, case, "self-assign", expected_version=0).status_code == 422
    r.login("owner")
    response = post(r, case, "self-assign", expected_version=0)
    assert response.status_code == 200, response.text
    assert post(r, case, "self-assign", expected_version=0).status_code == 409
    assert (
        post(
            r,
            case,
            "assign",
            expected_version=1,
            assignee_id=r.ids["peer"],
            reason="Cover shift",
        ).status_code
        == 403
    )
    r.login("lead")
    result = post(
        r,
        case,
        "assign",
        expected_version=1,
        assignee_id=r.ids["peer"],
        reason="Cover shift",
    )
    assert result.status_code == 200, result.text
    r.login("peer")
    assert (
        r.client.put(
            "/api/v1/routing/me/availability", json={"is_available": False}
        ).status_code
        == 200
    )
    r.login("lead")
    assert (
        post(
            r,
            case,
            "assign",
            expected_version=2,
            assignee_id=r.ids["peer"],
            reason="Unavailable",
        ).status_code
        == 422
    )
    r.login("auditor")
    assert handoff(r, case).status_code == 403
    s = state(r, case)
    assert not any(s["permissions"].values())


def test_esc_bulk_is_all_or_nothing_owner_preserved(routing):
    r = routing
    one = r.create()
    two = r.create()
    url = "/api/v1/routing/me/handover"
    body = {"assignee_id": r.ids["peer"], "reason": "Annual leave", "ticket_ids": [one]}
    assert r.client.post(url, json=body).status_code == 409
    with r.factory() as db:
        assert db.get(Ticket, one).assignee_id == r.ids["owner"]
    body["ticket_ids"] = [one, two]
    with r.factory() as db:
        db.get(Ticket, two).current_tier = 1
        db.commit()
    assert r.client.post(url, json=body).status_code == 422
    with r.factory() as db:
        assert (
            db.get(Ticket, one).routing_version == 0
            and db.get(Ticket, one).assignee_id == r.ids["owner"]
        )
        db.get(Ticket, two).current_tier = 2
        db.commit()
    response = r.client.post(url, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["count"] == 2
    with r.factory() as db:
        for case in (one, two):
            t = db.get(Ticket, case)
            assert t.owner_id == r.ids["owner"] and t.assignee_id == r.ids["peer"]
        assert (
            len(
                db.scalars(
                    select(RoutingEvent).where(RoutingEvent.ticket_id.in_([one, two]))
                ).all()
            )
            == 2
        )


def test_esc_admin_configuration_and_target_validation(routing):
    r = routing
    case = r.create()
    assert (
        r.client.put("/api/v1/routing/policy", json={"s1_minutes": 5}).status_code
        == 403
    )
    r.login("admin")
    for minutes in (0, 1441):
        assert (
            r.client.put(
                "/api/v1/routing/policy", json={"s1_minutes": minutes}
            ).status_code
            == 422
        )
    assert (
        r.client.put(
            "/api/v1/routing/policy", json={"s1_minutes": 7, "enabled": True}
        ).status_code
        == 200
    )
    assert (
        r.client.put(
            f"/api/v1/routing/users/{r.ids['specialist']}/tier",
            json={"default_tier": 1},
        ).status_code
        == 200
    )
    assert (
        r.client.put(
            f"/api/v1/routing/teams/{r.teams[0]}/leader",
            json={"leader_id": r.ids["specialist"]},
        ).status_code
        == 422
    )
    assert (
        r.client.put(
            "/api/v1/routing/routes",
            json={"product_id": r.product, "tier": 1, "team_id": r.teams[1]},
        ).status_code
        == 200
    )
    assert handoff(r, case, assignee_id=r.ids["peer"]).status_code == 422
    assert handoff(r, case, tier=2).status_code == 422


def test_esc_job_s1_escalates_once_and_new_alerts_business_hours(routing):
    r = routing
    now = datetime(2026, 10, 27, 3, 0)
    case = r.create(severity="S1", created_at=now - timedelta(minutes=21))
    with r.factory() as db:
        first = run_routing_checks(db, now)
        assert first["escalated"] == 1
        t = db.get(Ticket, case)
        assert t.current_tier == 1 and t.owner_id == r.ids["owner"]
        notices = db.scalars(
            select(RoutingNotification).where(RoutingNotification.ticket_id == case)
        ).all()
        assert {"s1_unresponsive", "auto_escalated", "new_stalled"} <= {
            n.kind for n in notices
        }
        count = len(notices)
        assert run_routing_checks(db, now)["escalated"] == 0
        assert (
            len(
                db.scalars(
                    select(RoutingNotification).where(
                        RoutingNotification.ticket_id == case
                    )
                ).all()
            )
            == count
        )
        assert run_routing_checks(db, now + timedelta(minutes=16))["escalated"] == 1
        db.refresh(t)
        assert t.current_tier == 0
    r.login("lead")
    own = r.client.get("/api/v1/routing/notifications").json()
    assert own
    notice = own[0]["id"]
    r.login("owner")
    assert (
        r.client.post(f"/api/v1/routing/notifications/{notice}/read").status_code == 404
    )
    r.login("lead")
    assert (
        r.client.post(f"/api/v1/routing/notifications/{notice}/read").status_code == 200
    )


def test_esc_job_hours_holiday_response_and_no_destination(routing):
    r = routing
    now = datetime(2026, 10, 27, 3, 0)
    case = r.create(severity="S1", created_at=now - timedelta(minutes=21))
    with r.factory() as db:
        calendar = BusinessCalendar(name="ESC calendar " + uuid4().hex)
        db.add(calendar)
        db.flush()
        db.add(
            BusinessHoliday(
                business_calendar_id=calendar.id,
                holiday_date=now.date(),
                name="Holiday",
            )
        )
        db.flush()
        assert not within_business_hours(db, now, calendar.id)
        assert not within_business_hours(db, datetime(2026, 10, 25, 3), None)
        assert within_business_hours(db, datetime(2026, 10, 27, 1), None)
        assert not within_business_hours(db, datetime(2026, 10, 27, 10), None)
        db.get(User, r.ids["specialist"]).is_available = False
        db.commit()
        result = run_routing_checks(db, now)
        assert result["escalated"] == 0
        assert db.scalar(
            select(RoutingNotification.id).where(
                RoutingNotification.ticket_id == case,
                RoutingNotification.kind == "routing_blocked",
            )
        )
        db.get(Ticket, case).first_response_at = now
        db.commit()
        assert run_routing_checks(db, now + timedelta(minutes=20))["escalated"] == 0


def test_esc_response_and_closed_intervals(routing):
    r = routing
    case = r.create()
    s = state(r, case)
    result = post(r, case, "respond", expected_version=s["version"])
    assert result.status_code == 200, result.text
    assert result.json()["first_response_at"]
    assert (
        post(r, case, "respond", expected_version=result.json()["version"]).status_code
        == 409
    )
    result = r.client.patch(
        f"/api/v1/tickets/{case}/status",
        json={"status": "CANCELLED", "cancel_reason": "No longer required"},
    )
    assert result.status_code == 200, result.text
    with r.factory() as db:
        assert not db.scalar(
            select(TierInterval.id).where(TierInterval.open_ticket_id == case)
        )
    assert handoff(r, case).status_code == 409


def test_self_assign_permissions_match_recipient_validation(routing):
    r = routing
    case = r.create(assignee_id=None)
    r.login("specialist")
    assert not state(r, case)["permissions"]["self_assign"]
    r.login("owner")
    with r.factory() as db:
        db.get(User, r.ids["specialist"]).team_id = None
        db.execute(
            delete(ProductTierRoute).where(
                ProductTierRoute.product_id == r.product, ProductTierRoute.tier == 1
            )
        )
        db.commit()
    assert r.ids["specialist"] not in [
        u["id"] for u in state(r, case)["eligible_users"]
    ]


def test_mariadb_concurrent_pickup_has_one_winner(routing):
    from concurrent.futures import ThreadPoolExecutor

    r = routing
    with r.factory() as db:
        if db.bind.dialect.name != "mysql":
            pytest.skip("Real row-lock race is exercised on migrated MariaDB in CI")
    case = r.create(assignee_id=None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: post(r, case, "self-assign", expected_version=0), range(2)
            )
        )
    assert sorted(response.status_code for response in responses) == [200, 409]
    with r.factory() as db:
        assert (
            len(
                db.scalars(
                    select(RoutingEvent).where(RoutingEvent.ticket_id == case)
                ).all()
            )
            == 1
        )
        assert db.get(Ticket, case).owner_id == r.ids["owner"]


def test_worker_lease_roundtrips_second_precision(routing):
    r = routing
    now = datetime(2026, 10, 27, 3, 0, 0, 123456)
    with r.factory() as db:
        run_routing_checks(db, now)
        lease = db.get(RoutingJobLease, 1)
        assert lease.locked_until == datetime(2026, 10, 27, 3, 5)
        assert lease.last_success_at == datetime(2026, 10, 27, 3)
        assert "skipped" in run_routing_checks(db, now + timedelta(minutes=4))
        assert "skipped" not in run_routing_checks(db, now + timedelta(minutes=5))


def test_old_draft_publish_starts_fresh_new_and_s1_timers(routing):
    from app.services.routing import utcnow

    r = routing
    with r.factory() as db:
        instance = db.scalar(
            select(ProductInstance).where(ProductInstance.product_id == r.product)
        )
        organization = instance.organization_id
    response = r.client.post(
        "/api/v1/tickets",
        json={
            "subject": "Old draft publishing",
            "save_as_draft": True,
            "organization_id": organization,
            "contact_id": r.context["contact_id"],
            "channel": "phone",
        },
    )
    assert response.status_code == 201, response.text
    case = response.json()["id"]
    with r.factory() as db:
        db.get(Ticket, case).severity = "S1"
        db.get(Ticket, case).created_at = utcnow() - timedelta(days=2)
        db.commit()
    result = r.client.patch(f"/api/v1/tickets/{case}/status", json={"status": "NEW"})
    assert result.status_code == 200, result.text
    assert result.json()["ticket_no"]
    with r.factory() as db:
        result = run_routing_checks(db, utcnow() + timedelta(minutes=1))
        assert db.get(Ticket, case).routing_version == 1
        assert not db.scalar(
            select(RoutingNotification.id).where(RoutingNotification.ticket_id == case)
        )


def test_team_lead_role_receives_alert_without_explicit_leader_mapping(routing):
    from app.services.routing import leaders

    r = routing
    case = r.create()
    with r.factory() as db:
        db.delete(db.get(TeamRouting, r.teams[0]))
        db.flush()
        assert [u.id for u in leaders(db, db.get(Ticket, case))] == [r.ids["lead"]]
