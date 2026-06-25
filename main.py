from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Union
from datetime import datetime
import mongoengine
import os
import re
from auth import create_access_token, verify_password, admin_password, get_admin_token

MONGO_HOST = os.environ.get("MONGO_HOST", "mongodb")

if "default" not in mongoengine.connection._connections:
    mongoengine.connect(
        "resonate",
        host=MONGO_HOST,
        uuidRepresentation="pythonLegacy",
    )


class EventOut(BaseModel):
    id: str
    title: str
    date: str
    points: Optional[Union[list, dict]] = None
    extra: Optional[dict] = None
    images: Optional[list] = None


class EventCreate(BaseModel):
    title: str
    date: str
    points: Optional[Union[list, dict]] = None
    extra: Optional[dict] = None
    images: Optional[list] = None


class EventImage(BaseModel):
    filename: str
    name: str
    image_type: str = "optical"
    tile_url: Optional[str] = None


def _normalize_points(points) -> Optional[dict]:
    if not points:
        return None
    if isinstance(points, list):
        return {"type": "MultiPoint", "coordinates": points}
    return points


def _format_points(points) -> Optional[dict]:
    if not points or not isinstance(points, dict):
        return None
    coords = points.get("coordinates")
    if coords and isinstance(coords, list):
        return {"type": "MultiPoint", "coordinates": coords}
    return None


class Event(mongoengine.Document):
    title = mongoengine.StringField(required=True)
    date = mongoengine.DateTimeField(required=True)
    points = mongoengine.DictField(null=True, blank=True)
    extra = mongoengine.DictField(null=True, blank=True)
    images = mongoengine.ListField(null=True, blank=True)

    meta = {"collection": "events"}

    def __str__(self):
        return self.title


def get_db():
    return Event


app = FastAPI()


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.post("/api/admin/login", response_model=TokenResponse)
def admin_login(req: LoginRequest):
    if not verify_password(req.password, admin_password.hash):
        raise HTTPException(status_code=401, detail="Invalid password")
    return TokenResponse(access_token=create_access_token())


@app.post("/api/events", response_model=EventOut, status_code=201)
def store_event(event: EventCreate, db=Depends(get_db), _=Depends(get_admin_token)):
    parsed_date = datetime.fromisoformat(event.date)
    points = _normalize_points(event.points)

    doc = db(
        title=event.title,
        date=parsed_date,
        points=points,
        extra=event.extra,
        images=event.images or [],
    )
    doc.save()

    return EventOut(
        id=str(doc.id),
        title=doc.title,
        date=doc.date.isoformat(),
        points=_format_points(doc.points),
        extra=doc.extra,
        images=doc.images,
    )


@app.get("/api/events/{event_id}", response_model=EventOut)
def get_event(event_id: str, db=Depends(get_db), _=Depends(get_admin_token)):
    doc = db.objects(id=event_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    return EventOut(
        id=str(doc.id),
        title=doc.title,
        date=doc.date.isoformat(),
        points=_format_points(doc.points),
        extra=doc.extra,
        images=doc.images,
    )


@app.get("/api/events", response_model=List[EventOut])
def list_events(db=Depends(get_db), _=Depends(get_admin_token)):
    docs = db.objects().order_by('-date')
    return [
        EventOut(
            id=str(doc.id),
            title=doc.title,
            date=doc.date.isoformat(),
            points=_format_points(doc.points),
            extra=doc.extra,
            images=doc.images,
        )
        for doc in docs
    ]


@app.get("/api/public/events", response_model=List[EventOut])
def list_events_public(db=Depends(get_db)):
    docs = db.objects().order_by('-date')
    return [
        EventOut(
            id=str(doc.id),
            title=doc.title,
            date=doc.date.isoformat(),
            points=_format_points(doc.points),
            extra=doc.extra,
            images=doc.images,
        )
        for doc in docs
    ]


@app.put("/api/events/{event_id}", response_model=EventOut)
def update_event(event_id: str, event: EventCreate, db=Depends(get_db), _=Depends(get_admin_token)):
    doc = db.objects(id=event_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    parsed_date = datetime.fromisoformat(event.date)
    points = _normalize_points(event.points)

    doc.title = event.title
    doc.date = parsed_date
    doc.points = points
    doc.extra = event.extra
    if event.images is not None:
        doc.images = event.images
    doc.save()

    return EventOut(
        id=str(doc.id),
        title=doc.title,
        date=doc.date.isoformat(),
        points=_format_points(doc.points),
        extra=doc.extra,
        images=doc.images,
    )


@app.delete("/api/events/{event_id}", status_code=204)
def delete_event(event_id: str, db=Depends(get_db), _=Depends(get_admin_token)):
    doc = db.objects(id=event_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc.delete()


IMAGES_DIR = os.environ.get("IMAGES_DIR", "/app/images")
ALLOWED_UPLOAD_TYPES = {"image/tiff", "image/png", "image/jpeg", "application/octet-stream"}
MAX_UPLOAD_MB = 50

try:
    if os.path.isdir(IMAGES_DIR):
        app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
    else:
        os.makedirs(IMAGES_DIR, exist_ok=True)
        app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
except OSError:
    pass  # May be read-only in tests


@app.post("/api/events/{event_id}/images")
async def upload_image(
    event_id: str,
    file: UploadFile = File(...),
    name: str = Form(...),
    image_type: str = Form("optical"),
    db=Depends(get_db),
    _=Depends(get_admin_token),
):
    doc = db.objects(id=event_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")

    if file.content_type and file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(status_code=400, detail=f"File type '{file.content_type}' not allowed. Accepted: {', '.join(ALLOWED_UPLOAD_TYPES)}")

    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_MB}MB limit")

    safe_name = re.sub(r"[^\w\-.]", "_", file.filename or "upload.bin")
    images_dir = os.environ.get("IMAGES_DIR", IMAGES_DIR)
    filename = f"{event_id}_{datetime.now().timestamp()}_{safe_name}"
    filepath = os.path.join(images_dir, os.path.basename(filename))
    os.makedirs(images_dir, exist_ok=True)

    with open(filepath, "wb") as f:
        f.write(content)

    bounds = None
    preview_filename = None
    if filename.lower().endswith(('.tif', '.tiff')):
        try:
            import rasterio

            with rasterio.open(filepath) as src:
                bounds = list(src.bounds)

                # Create a simple preview as PNG
                preview_filename = filename.rsplit('.', 1)[0] + '_preview.png'
                preview_path = os.path.join(images_dir, preview_filename)

                # Read bands and create a small preview
                if src.count >= 3:
                    data = src.read([1, 2, 3], out_shape=(3, 500, 500), resampling=rasterio.enums.Resampling.bilinear)
                else:
                    data = src.read(1, out_shape=(1, 500, 500), resampling=rasterio.enums.Resampling.bilinear)

                # Write as PNG using rasterio's profile
                with rasterio.open(
                    preview_path, 'w',
                    driver='PNG',
                    width=data.shape[2],
                    height=data.shape[1],
                    count=data.shape[0],
                    dtype=data.dtype
                ) as dst:
                    dst.write(data)

                print(f"Created preview: {preview_filename}")

        except Exception as e:
            import traceback
            print(f"Failed to extract bounds or create preview: {e}")
            traceback.print_exc()
            bounds = None
            preview_filename = None

    image_data = {
        "filename": filename,
        "name": name,
        "image_type": image_type,
        "bounds": bounds,
        "preview": preview_filename,
    }

    if not doc.images:
        doc.images = []
    doc.images.append(image_data)
    doc.save()

    return {"status": "ok", "image": image_data}


@app.get("/api/events/{event_id}/images")
def get_event_images(event_id: str, db=Depends(get_db), _=Depends(get_admin_token)):
    doc = db.objects(id=event_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"images": doc.images or []}
