"""ADO-01 / ADO-04 and CAP-04 evidence."""
from test_tickets import capture  # noqa: F401


def test_three_fields_are_enough_and_capture_time_is_reported(capture):
    client, _, _, data, _ = capture
    minimal = {"organization_id": data["organization_id"], "subject": "Projector shows no signal",
               "channel": "phone", "capture_seconds": 24}
    created = client.post("/api/v1/tickets", json=minimal)
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "NEW"  # ADO-04: no fourth mandatory field
    slow = client.post("/api/v1/tickets", json=dict(minimal, subject="Teacher cannot upload marks",
                                                    capture_seconds=48))
    assert slow.status_code == 201, slow.text
    draft = client.post("/api/v1/tickets", json={"subject": "Half typed", "capture_seconds": 5})
    assert draft.json()["status"] == "DRAFT"

    report = client.get("/api/v1/reports/capture-time").json()
    assert report["required_fields"] == ["customer", "subject", "channel"]
    assert report["overall"]["count"] == 2  # drafts are not counted
    assert report["overall"]["within_target_pct"] == 50.0
    assert report["overall"]["median_seconds"] == 36
