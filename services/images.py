import logging
import os
import re
from datetime import datetime

import filetype
from fastapi import HTTPException

from models import Event

logger = logging.getLogger(__name__)

IMAGES_DIR = os.environ.get("IMAGES_DIR", "/app/images")
ALLOWED_UPLOAD_TYPES = {"image/tiff", "image/png", "image/jpeg"}
MAX_UPLOAD_MB = 50


def validate_upload(content: bytes, content_type: str | None) -> None:
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_MB}MB limit")

    kind = filetype.guess(content)
    if kind is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to determine file type. Only PNG, JPEG, and TIFF are allowed.",
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


def process_tif(filename: str, filepath: str) -> tuple[list | None, str | None]:
    bounds = None
    preview_filename = None

    if not filename.lower().endswith((".tif", ".tiff")):
        return bounds, preview_filename

    try:
        import rasterio

        with rasterio.open(filepath) as src:
            bounds = list(src.bounds)

            preview_filename = filename.rsplit(".", 1)[0] + "_preview.png"
            images_dir = os.environ.get("IMAGES_DIR", IMAGES_DIR)
            preview_path = os.path.join(images_dir, preview_filename)

            if src.count >= 3:
                data = src.read(
                    [1, 2, 3],
                    out_shape=(3, 500, 500),
                    resampling=rasterio.enums.Resampling.bilinear,
                )
            else:
                data = src.read(
                    1,
                    out_shape=(1, 500, 500),
                    resampling=rasterio.enums.Resampling.bilinear,
                )

            with rasterio.open(
                preview_path,
                "w",
                driver="PNG",
                width=data.shape[2],
                height=data.shape[1],
                count=data.shape[0],
                dtype=data.dtype,
            ) as dst:
                dst.write(data)

            logger.info("Created preview: %s", preview_filename)

    except Exception:
        logger.warning("Failed to extract bounds or create preview", exc_info=True)
        bounds = None
        preview_filename = None

    return bounds, preview_filename


def upload_image(event_id: str, content: bytes, name: str, image_type: str, filename: str | None = None) -> dict:
    doc = Event.objects(id=event_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")

    validate_upload(content, None)

    safe_name = sanitize_filename(filename)
    saved_filename = save_file(content, event_id, safe_name)
    images_dir = os.environ.get("IMAGES_DIR", IMAGES_DIR)
    filepath = os.path.join(images_dir, os.path.basename(saved_filename))

    bounds, preview_filename = process_tif(saved_filename, filepath)

    image_data = {
        "filename": saved_filename,
        "name": name,
        "image_type": image_type,
        "bounds": bounds,
        "preview": preview_filename,
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
