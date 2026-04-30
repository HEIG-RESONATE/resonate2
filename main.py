from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import mongoengine


def _connect():
    """Connect to MongoDB only when first needed."""
    if not mongoengine.connection.get_connection("resonate"):
        mongoengine.connect(
            "resonate",
            uuidRepresentation="pythonLegacy",
        )


mongoengine.disconnect()  # Clear default connection set by conftest


class EventOut(BaseModel):
    id: str
    title: str
    date: str
    points: Optional[list] = None


class EventCreate(BaseModel):
    title: str
    date: str
    points: Optional[list] = None


class Event(mongoengine.Document):
    title = mongoengine.StringField(required=True)
    date = mongoengine.DateTimeField(required=True)
    points = mongoengine.DictField(null=True, blank=True)

    meta = {"collection": "events"}


def get_db():
    _connect()
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/events", response_model=EventOut, status_code=201)
def store_event(event: EventCreate, db=Depends(get_db)):
    parsed_date = datetime.fromisoformat(event.date)

    points = event.points
    if isinstance(points, list):
        points = {"type": "MultiPoint", "coordinates": points}

    doc = db(
        title=event.title,
        date=parsed_date,
        points=points,
    )
    doc.save()

    pts = doc.points
    if pts and isinstance(pts.get("coordinates"), list):
        pts = {"type": "MultiPoint", "coordinates": pts["coordinates"]}

    return EventOut(
        id=str(doc.id),
        title=doc.title,
        date=doc.date.isoformat(),
        points=pts,
    )


@app.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: str, db=Depends(get_db)):
    doc = db.objects(id=event_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    pts = doc.points
    if pts and isinstance(pts.get("coordinates"), list):
        pts = {"type": "MultiPoint", "coordinates": pts["coordinates"]}

    return EventOut(
        id=str(doc.id),
        title=doc.title,
        date=doc.date.isoformat(),
        points=pts,
    )
