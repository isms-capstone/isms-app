"""Preserve the existing WRK wire format using disposable API fixtures."""
from test_tickets import capture


def test_create_worklog_internal_and_public(capture):
    client, _, _, context, _ = capture
    created = client.post('/api/v1/tickets', json=context | {'subject': 'Legacy WRK', 'channel': 'phone'}).json()
    path = f"/api/v1/tickets/{created['id']}/worklogs"
    for payload in ({'message': 'Internal note for team only', 'is_internal': True},
                    {'message': 'Public reply to customer', 'is_internal': False, 'channel': 'portal'}):
        response = client.post(path, json=payload)
        assert response.status_code == 201, response.text
        assert response.json()['message'] == payload['message']
        assert response.json()['is_internal'] is payload['is_internal']
    assert len(client.get(path).json()) == 2


def test_worklog_validation_empty_message(capture):
    client, _, _, _, _ = capture
    row = client.post('/api/v1/tickets', json={'subject': 'Draft', 'save_as_draft': True}).json()
    path = f"/api/v1/tickets/{row['id']}/worklogs"
    assert client.post(path, json={'message': '   ', 'is_internal': True}).status_code == 422
    # Public replies must explicitly record their actual channel, never infer intake.
    assert client.post(path, json={'message': 'Reply', 'is_internal': False}).status_code == 422


def test_create_public_reply_with_channel(capture):
    client, _, _, _, _ = capture
    row = client.post('/api/v1/tickets', json={'subject': 'Draft', 'save_as_draft': True}).json()
    response = client.post(f"/api/v1/tickets/{row['id']}/worklogs",
                           json={'message': 'แจ้งอัปเดตผ่าน LINE OA', 'is_internal': False, 'channel': 'line_oa'})
    assert response.status_code == 201, response.text
    assert response.json()['channel'] == 'line_oa'
