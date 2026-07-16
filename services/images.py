import os
import re
import uuid
from datetime import datetime
from urllib.parse import quote

import filetype
from fastapi import HTTPException
from mongoengine.errors import ValidationError

from models import Event

IMAGES_DIR = os.environ.get("IMAGES_DIR", "/app/images")
ALLOWED_UPLOAD_TYPES = {"image/png", "image/jpeg"}
MAX_UPLOAD_MB = 50


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


def get_image_access(event_id: str, image_id: str, variant: str) -> dict:
    """Resolve an event image to its stable, UI-served overlay path."""
    _, image = get_image_for_event(event_id, image_id)
    filename = image.get("preview") if variant == "preview" else image.get("filename")
    if not filename:
        raise HTTPException(status_code=404, detail="Preview not available" if variant == "preview" else "Image not found")

    content_type = image.get("content_type") or "application/octet-stream"
    return {
        "image_id": image_id,
        "event_id": event_id,
        "variant": variant,
        "url_path": f"/images/{quote(os.path.basename(filename), safe='')}",
        "filename": image.get("filename", "image"),
        "content_type": content_type,
    }
