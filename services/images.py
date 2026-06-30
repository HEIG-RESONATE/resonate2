import logging
import os
import re
from datetime import datetime

import filetype
from fastapi import HTTPException

from models import Event

logger = logging.getLogger(__name__)

IMAGES_DIR = os.environ.get("IMAGES_DIR", "/app/images")
ALLOWED_UPLOAD_TYPES = {"image/png", "image/jpeg"}
MAX_UPLOAD_MB = 50


def validate_upload(content: bytes, content_type: str | None) -> None:
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

    validate_upload(content, None)

    safe_name = sanitize_filename(filename)
    saved_filename = save_file(content, event_id, safe_name)

    image_data = {
        "filename": saved_filename,
        "name": name,
        "image_type": image_type,
        "bounds": bounds,
        "preview": saved_filename,
    }

    if not doc.images:
        doc.images = []
    doc.images.append(image_data)
    doc.save()

    return image_data


def get_event_images(event_id: str) -> list:
    doc = Event.objects(id=event_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return doc.images or []
