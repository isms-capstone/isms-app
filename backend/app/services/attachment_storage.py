"""Private object storage and validation for case evidence."""
import io
import os
import zipfile
from functools import lru_cache
from pathlib import PurePosixPath

from fastapi import HTTPException
from minio import Minio
from minio.error import S3Error
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 25 * 1024 * 1024
BUCKET = os.getenv('MINIO_ATTACHMENT_BUCKET', 'isms-attachments')
IMAGE_TYPES = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp', 'GIF': 'image/gif'}


@lru_cache(maxsize=1)
def storage():
    endpoint = os.getenv('MINIO_ENDPOINT')
    key, secret = os.getenv('MINIO_ACCESS_KEY'), os.getenv('MINIO_SECRET_KEY')
    if not (endpoint and key and secret):
        raise HTTPException(503, 'Attachment storage is not configured')
    return Minio(endpoint, access_key=key, secret_key=secret,
                 secure=os.getenv('MINIO_SECURE', 'true').lower() == 'true')


def put_object(key, stream, size, mime):
    client = storage()
    if not client.bucket_exists(BUCKET):
        try:
            client.make_bucket(BUCKET)
        except S3Error as exc:
            if exc.code != 'BucketAlreadyOwnedByYou':
                raise
    client.put_object(BUCKET, key, stream, size, content_type=mime)


def store_attachment(db, ticket_id, stream, original_name, uploaded_by_id, allowed_types=None):
    """Validate, upload and stage one attachment row. Returns (row, object_keys).

    The caller commits the session; on failure it must call discard(object_keys)
    so that no orphan object remains without database metadata."""
    from io import BytesIO
    from uuid import uuid4

    from app.db.models.ticket_attachment import TicketAttachment

    size, mime, thumbnail = inspect_file(stream, original_name)
    if allowed_types is not None and mime not in allowed_types:
        raise HTTPException(415, 'Unsupported attachment type')
    key = f'{ticket_id}/{uuid4().hex}'
    written = []
    try:
        put_object(key, stream, size, mime)
        written.append(key)
        if thumbnail:
            put_object(key + '.thumb.webp', BytesIO(thumbnail), len(thumbnail), 'image/webp')
            written.append(key + '.thumb.webp')
    except Exception:
        discard(written)
        raise
    row = TicketAttachment(ticket_id=ticket_id, original_name=original_name[:255],
                           stored_name='minio/' + key, content_type=mime,
                           size_bytes=size, uploaded_by_id=uploaded_by_id)
    db.add(row)
    return row, written


def discard(keys):
    import logging

    for key in keys:
        try:
            storage().remove_object(BUCKET, key)
        except Exception:
            logging.getLogger(__name__).exception('Could not remove incomplete attachment object')


def image_thumbnail(stream):
    try:
        stream.seek(0)
        with Image.open(stream) as image:
            mime = IMAGE_TYPES.get(image.format)
            if not mime or image.width * image.height > 24_000_000:
                raise HTTPException(415, 'Unsupported image type or dimensions')
            image = ImageOps.exif_transpose(image)
            image.thumbnail((320, 320))
            buffer = io.BytesIO()
            image.save(buffer, format='WEBP')
            return mime, buffer.getvalue()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        raise HTTPException(415, 'Invalid image attachment') from None
    finally:
        stream.seek(0)


def inspect_file(stream, name):
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    if size > MAX_BYTES:
        raise HTTPException(413, 'Maximum attachment size is 25 MB')
    if not size:
        raise HTTPException(422, 'Attachment is empty')
    stream.seek(0)
    head = stream.read(4096)
    stream.seek(0)
    suffix = PurePosixPath(name).suffix.lower()
    if suffix in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
        mime, thumbnail = image_thumbnail(stream)
        return size, mime, thumbnail
    if suffix == '.pdf' and head.startswith(b'%PDF-'):
        return size, 'application/pdf', None
    if suffix == '.mp4' and head[4:8] == b'ftyp':
        return size, 'video/mp4', None
    if suffix == '.webm' and head.startswith(b'\x1a\x45\xdf\xa3') and b'webm' in head:
        return size, 'video/webm', None
    if name.lower().endswith(('.log.gz', '.txt.gz')) and head.startswith(b'\x1f\x8b\x08'):
        return size, 'application/gzip', None
    if suffix == '.zip' and head.startswith(b'PK\x03\x04'):
        try:
            with zipfile.ZipFile(stream) as archive:
                files = [item for item in archive.infolist() if not item.is_dir()]
                if files and all(PurePosixPath(item.filename).suffix.lower() in {'.log', '.txt'} for item in files):
                    return size, 'application/zip', None
        except (zipfile.BadZipFile, OSError, ValueError):
            pass
        finally:
            stream.seek(0)
    raise HTTPException(415, 'Unsupported or invalid attachment type')
