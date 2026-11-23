from datetime import datetime, timedelta, timezone
from io import BytesIO

from jose import jwt
from PIL import Image

from app.core.config import settings
from app.services import attachment_storage
from test_tickets import capture


def test_private_attachment_thumbnail_and_expiry(capture, monkeypatch):
    client, app, _, context, _ = capture
    objects = {}

    class StoredObject(BytesIO):
        def stream(self, size):
            while chunk := self.read(size):
                yield chunk

        def release_conn(self):
            pass

    class Storage:
        def get_object(self, bucket, key):
            return StoredObject(objects[key])

    def put(key, stream, size, mime):
        objects[key] = stream.read()
        assert len(objects[key]) == size

    monkeypatch.setattr(attachment_storage, 'storage', Storage)
    monkeypatch.setattr(attachment_storage, 'put_object', put)
    ticket = client.post('/api/v1/tickets', json={
        **context, 'subject': 'Attachment QA', 'channel': 'phone',
    }).json()
    path = f"/api/v1/tickets/{ticket['id']}/attachments"
    image = BytesIO()
    Image.new('RGB', (640, 480), 'navy').save(image, format='PNG')
    assert client.post(path, files={'file': ('fake.png', b'<html>', 'image/png')}).status_code == 415
    assert client.post(path, files={'file': ('large.pdf', b'%PDF-' + b'x' * attachment_storage.MAX_BYTES,
                                             'application/pdf')}).status_code == 413
    upload = client.post(path, files={'file': ('proof.png', image.getvalue(), 'image/png')})
    assert upload.status_code == 201, upload.text
    row = upload.json()
    assert len(objects) == 2
    assert client.get(row['download_url']).content == image.getvalue()
    thumb = client.get(row['thumbnail_url'])
    assert thumb.status_code == 200
    assert Image.open(BytesIO(thumb.content)).size == (320, 240)
    assert client.get(row['preview_url']).headers['content-disposition'].startswith('inline')
    bare = row['download_url'].split('?')[0]
    assert client.get(bare).status_code == 403
    expired = jwt.encode({
        'type': 'attachment', 'sub': str(ticket['created_by_id']), 'ticket': ticket['id'],
        'file': row['id'], 'exp': datetime.now(timezone.utc) - timedelta(seconds=1),
    }, settings.SECRET_KEY, algorithm='HS256')
    assert client.get(bare, params={'access': expired}).status_code == 403

    from types import SimpleNamespace
    from app.api.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=ticket['created_by_id'] + 100, role=SimpleNamespace(name='Agent'))
    assert client.get(row['download_url']).status_code == 403
    # SRS 3.2: another support agent can triage the evidence with their own link,
    # but cannot add files to a case they do not take part in.
    listed = client.get(path)
    assert listed.status_code == 200
    assert client.get(listed.json()[0]['download_url']).content == image.getvalue()
    assert client.post(path, files={'file': ('more.png', image.getvalue(), 'image/png')}).status_code == 403
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=ticket['created_by_id'] + 101, role=SimpleNamespace(name='Auditor'))
    assert client.get(path).status_code == 403
