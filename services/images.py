import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone

import filetype
from fastapi import HTTPException
from mongoengine.errors import ValidationError

from auth import SECRET_KEY
from models import Event

logger = logging.getLogger(__name__)

IMAGES_DIR = os.environ.get("IMAGES_DIR", "/app/images")
ALLOWED_UPLOAD_TYPES = {"image/png", "image/jpeg"}
MAX_UPLOAD_MB = 50
IMAGE_ACCESS_TTL_SECONDS = 300


def validate_upload(content: bytes, content_type: str | None) -> str:
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_MB}MB limit")

    kind = filetype.guess(content)
    if kind is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to determine file type. Only PNG and JPEG are allowed.",
        )
    if kind.mime not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{kind.mime}' not allowed. Accepted: {', '.join(ALLOWED_UPLOAD_TYPES)}",
        )
    return kind.mime


def sanitize_filename(filename: str | None) -> str:
    return re.sub(r"[^\w\-.]", "_", filename or "upload.bin")


def save_file(content: bytes, event_id: str, safe_name: str) -> str:
    images_dir = os.environ.get("IMAGES_DIR", IMAGES_DIR)
    filename = f"{event_id}_{datetime.now().timestamp()}_{safe_name}"
    filepath = os.path.join(images_dir, os.path.basename(filename))
    os.makedirs(images_dir, exist_ok=True)

    with open(filepath, "wb") as f:
        f.write(content)

    return filename


def parse_bounds(bounds_str: str | None) -> list[float] | None:
    if not bounds_str:
        return None
    try:
        parts = [float(x.strip()) for x in bounds_str.split(",")]
        if len(parts) != 4:
            raise HTTPException(status_code=400, detail="Bounds must have exactly 4 values: west,south,east,north")
        return parts
    except (ValueError, HTTPException) as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=400, detail="Invalid bounds format. Use: west,south,east,north")


def upload_image(event_id: str, content: bytes, name: str, image_type: str, bounds: list[float] | None = None, filename: str | None = None) -> dict:
    doc = Event.objects(id=event_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")

    content_type = validate_upload(content, None)

    safe_name = sanitize_filename(filename)
    saved_filename = save_file(content, event_id, safe_name)

    image_data = {
        "id": str(uuid.uuid4()),
        "filename": saved_filename,
        "name": name,
        "image_type": image_type,
        "bounds": bounds,
        "preview": saved_filename,
        "content_type": content_type,
    }

    if not doc.images:
        doc.images = []
    doc.images.append(image_data)
    doc.save()

    return image_data


def ensure_image_ids(doc: Event) -> list:
    """Backfill immutable opaque IDs for legacy image metadata on first access."""
    images = doc.images or []
    changed = False
    for image in images:
        if not image.get("id"):
            image["id"] = str(uuid.uuid4())
            changed = True
    if changed:
        doc.images = images
        doc.save()
    return images


def get_event_images(event_id: str) -> list:
    doc = Event.objects(id=event_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return ensure_image_ids(doc)


def _access_ttl_seconds() -> int:
    try:
        configured = int(os.environ.get("IMAGE_ACCESS_TTL_SECONDS", IMAGE_ACCESS_TTL_SECONDS))
    except ValueError:
        configured = IMAGE_ACCESS_TTL_SECONDS
    return min(max(configured, 1), 900)


def _encode_access_token(payload: dict) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
    signature = hmac.new(
        SECRET_KEY.encode(), b"satellite-image-access:v1." + encoded, hashlib.sha256
    ).digest()
    return f"{encoded.decode()}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def _decode_access_token(token: str) -> dict:
    try:
        encoded, provided_signature = token.split(".", 1)
        expected_signature = hmac.new(
            SECRET_KEY.encode(), f"satellite-image-access:v1.{encoded}".encode(), hashlib.sha256
        ).digest()
        actual_signature = base64.urlsafe_b64decode(provided_signature + "=" * (-len(provided_signature) % 4))
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if not hmac.compare_digest(expected_signature, actual_signature) or payload["expires_at"] <= time.time():
            raise ValueError
        if payload["variant"] not in {"preview", "original"}:
            raise ValueError
        return payload
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error):
        raise HTTPException(status_code=404, detail="Image not found")


def get_image_for_event(event_id: str, image_id: str) -> tuple[Event, dict]:
    try:
        doc = Event.objects(id=event_id).first()
    except ValidationError:
        doc = None
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    image = next((item for item in ensure_image_ids(doc) if item.get("id") == image_id), None)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return doc, image


def get_image_access(event_id: str, image_id: str, variant: str, base_url: str) -> dict:
    _, image = get_image_for_event(event_id, image_id)
    filename = image.get("preview") if variant == "preview" else image.get("filename")
    if not filename:
        raise HTTPException(status_code=404, detail="Preview not available" if variant == "preview" else "Image not found")

    expires_at = int(time.time()) + _access_ttl_seconds()
    token = _encode_access_token({
        "event_id": event_id,
        "image_id": image_id,
        "variant": variant,
        "expires_at": expires_at,
    })
    content_type = image.get("content_type") or "application/octet-stream"
    return {
        "image_id": image_id,
        "event_id": event_id,
        "variant": variant,
        "url": f"{base_url.rstrip('/')}/api/satellite-image-access/{token}",
        "filename": image.get("filename", "image"),
        "content_type": content_type,
        "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def resolve_signed_image(token: str) -> tuple[str, str]:
    """Resolve a signed token to a local file without exposing storage paths."""
    payload = _decode_access_token(token)
    _, image = get_image_for_event(payload["event_id"], payload["image_id"])
    filename = image.get("preview") if payload["variant"] == "preview" else image.get("filename")
    if not filename:
        raise HTTPException(status_code=404, detail="Image not found")
    filepath = os.path.join(os.environ.get("IMAGES_DIR", IMAGES_DIR), os.path.basename(filename))
    if not os.path.isfile(filepath):
        logger.warning("Signed image access referenced a missing file")
        raise HTTPException(status_code=404, detail="Image not found")
    return filepath, image.get("content_type") or "application/octet-stream"
