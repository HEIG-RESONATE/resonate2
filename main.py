from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import mongoengine
import os

from schemas import CarouselImage, EventCreate, EventOut, EventUpdate, LoginRequest, TokenResponse
from models import Event
from auth import create_access_token, verify_password, admin_password, get_admin_token
from services import events as event_service
from services import images as image_service

MONGO_HOST = os.environ.get("MONGO_HOST", "mongodb")

if "default" not in mongoengine.connection._connections:
    mongoengine.connect(
        "resonate",
        host=MONGO_HOST,
        uuidRepresentation="pythonLegacy",
    )

limiter = Limiter(key_func=get_remote_address)

app = FastAPI()
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many login attempts. Try again later."},
    )


@app.post("/api/admin/login", response_model=TokenResponse)
@limiter.limit("15/minute")
def admin_login(request: Request, req: LoginRequest):
    if not verify_password(req.password, admin_password.hash):
        raise HTTPException(status_code=401, detail="Invalid password")
    return TokenResponse(access_token=create_access_token())


@app.get("/api/events", response_model=list[EventOut])
def list_events(_=Depends(get_admin_token)):
    return event_service.list_events()


@app.get("/api/events/{event_id}", response_model=EventOut)
def get_event(event_id: str, _=Depends(get_admin_token)):
    return event_service.get_event(event_id)


@app.post("/api/events", response_model=EventOut, status_code=201)
def store_event(event: EventCreate, _=Depends(get_admin_token)):
    return event_service.create_event(
        title=event.title,
        date=event.date,
        points=event.points,
        extra=event.extra,
        images=event.images,
        carousel_images=[c.model_dump() for c in event.carousel_images] if event.carousel_images else None,
        news=[n.model_dump() for n in event.news] if event.news else None,
    )


@app.put("/api/events/{event_id}", response_model=EventOut)
def update_event(event_id: str, event: EventUpdate, _=Depends(get_admin_token)):
    payload = event.model_dump(exclude_unset=True)
    if "carousel_images" in payload:
        payload["carousel_images"] = [c.model_dump() for c in event.carousel_images] if event.carousel_images else []
    if "news" in payload:
        payload["news"] = [n.model_dump() for n in event.news] if event.news else []
    return event_service.update_event(event_id=event_id, **payload)


@app.delete("/api/events/{event_id}", status_code=204)
def delete_event(event_id: str, _=Depends(get_admin_token)):
    event_service.delete_event(event_id)


async def _upload_satellite_image(
    event_id: str,
    file: UploadFile = File(...),
    name: str = Form(...),
    image_type: str = Form("optical"),
    bounds: str = Form(None),
    _=Depends(get_admin_token),
):
    content = await file.read()
    parsed_bounds = image_service.parse_bounds(bounds)
    image_data = image_service.upload_image(
        event_id=event_id,
        content=content,
        name=name,
        image_type=image_type,
        bounds=parsed_bounds,
        filename=file.filename,
    )
    return image_data


@app.post("/api/events/{event_id}/images")
async def upload_image(
    event_id: str,
    file: UploadFile = File(...),
    name: str = Form(...),
    image_type: str = Form("optical"),
    bounds: str = Form(None),
    _=Depends(get_admin_token),
):
    image_data = await _upload_satellite_image(event_id, file, name, image_type, bounds, _)
    return {"status": "ok", "image": image_data}


@app.post("/api/events/{event_id}/satellite-images")
async def upload_satellite_image(
    event_id: str,
    file: UploadFile = File(...),
    name: str = Form(...),
    image_type: str = Form("optical"),
    bounds: str = Form(None),
    _=Depends(get_admin_token),
):
    image_data = await _upload_satellite_image(event_id, file, name, image_type, bounds, _)
    return {"status": "ok", "satellite_image": image_data}


@app.get("/api/events/{event_id}/images")
def get_event_images(event_id: str, _=Depends(get_admin_token)):
    return {"images": image_service.get_event_images(event_id)}


@app.get("/api/events/{event_id}/satellite-images")
def get_satellite_images(event_id: str, _=Depends(get_admin_token)):
    return {"satellite_images": image_service.get_event_images(event_id)}


@app.get("/api/events/{event_id}/satellite-images/{image_id}/access")
def get_satellite_image_access(
    event_id: str,
    image_id: str,
    request: Request,
    variant: str = Query("preview", pattern="^(preview|original)$"),
    _=Depends(get_admin_token),
):
    return image_service.get_image_access(event_id, image_id, variant, str(request.base_url))


@app.get("/api/satellite-image-access/{token}")
def serve_signed_satellite_image(token: str):
    filepath, content_type = image_service.resolve_signed_image(token)
    return FileResponse(filepath, media_type=content_type)


@app.get("/api/public/events", response_model=list[EventOut])
def list_events_public():
    return event_service.list_events()
