from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import mongoengine
from auth import create_access_token, verify_password, admin_password


mongoengine.connect(
    "resonate",
    uuidRepresentation="pythonLegacy",
)


class DocumentOut(BaseModel):
    id: str
    source: str
    text: str
    coordinates: Optional[dict] = None


class DocumentCreate(BaseModel):
    source: str
    text: str
    coordinates: Optional[dict] = None


class Document(mongoengine.Document):
    source = mongoengine.StringField(required=True)
    text = mongoengine.StringField(required=True)
    coordinates = mongoengine.GeoPointField()

    meta = {"collection": "documents"}


def get_db():
    return Document


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


@app.post("/documents", response_model=DocumentOut, status_code=201)
def store_document(document: DocumentCreate, db = Depends(get_db)):
    coords = document.coordinates
    if isinstance(coords, dict):
        coords = (coords["lat"], coords["lng"])

    doc = db(
        source=document.source,
        text=document.text,
        coordinates=coords,
    )
    doc.save()
    coords = doc.coordinates
    if isinstance(coords, (list, tuple)):
        coords = {"lat": coords[0], "lng": coords[1]}
    return DocumentOut(
        id=str(doc.id),
        source=doc.source,
        text=doc.text,
        coordinates=coords,
    )


@app.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, db = Depends(get_db)):
    doc = db.objects(id=doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    coords = doc.coordinates
    if isinstance(coords, (list, tuple)):
        coords = {"lat": coords[0], "lng": coords[1]}
    return DocumentOut(
        id=str(doc.id),
        source=doc.source,
        text=doc.text,
        coordinates=coords,
    )
