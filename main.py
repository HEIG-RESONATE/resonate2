from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional


app = FastAPI()


def get_db():
    from pymongo import MongoClient

    client = MongoClient("mongodb://mongodb:27017")
    return client.documents.document


class DocumentCreate(BaseModel):
    source: str
    text: str
    coordinates: Optional[dict] = None


class DocumentOut(BaseModel):
    id: str
    source: str
    text: str
    coordinates: Optional[dict] = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/documents", response_model=DocumentOut, status_code=201)
def store_document(document: DocumentCreate, db = Depends(get_db)):
    result = db.insert_one(document.model_dump(exclude="id"))
    return DocumentOut(
        id=str(result.inserted_id),
        source=document.source,
        text=document.text,
        coordinates=document.coordinates,
    )


@app.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, db = Depends(get_db)):
    doc = db.find_one({"_id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return DocumentOut(
        id=str(doc["_id"]),
        source=doc["source"],
        text=doc["text"],
        coordinates=doc.get("coordinates"),
    )
