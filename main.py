from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Union
from datetime import datetime
import mongoengine
import os
from auth import create_access_token, verify_password, admin_password, get_admin_token

MONGO_HOST = os.environ.get("MONGO_HOST", "mongodb")

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


class EventCreate(BaseModel):
    title: str
    date: str
    points: Optional[Union[list, dict]] = None


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
    )
    doc.save()

    return EventOut(
        id=str(doc.id),
        title=doc.title,
        date=doc.date.isoformat(),
        points=_format_points(doc.points),
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
    doc.save()

    return EventOut(
        id=str(doc.id),
        title=doc.title,
        date=doc.date.isoformat(),
        points=_format_points(doc.points),
    )


@app.delete("/api/events/{event_id}", status_code=204)
def delete_event(event_id: str, db=Depends(get_db), _=Depends(get_admin_token)):
    doc = db.objects(id=event_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc.delete()
