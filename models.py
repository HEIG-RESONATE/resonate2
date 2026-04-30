from pydantic import BaseModel, Field
from typing import Optional


class DocumentCreate(BaseModel):
    source: str
    text: str
    coordinates: Optional[dict] = None


class DocumentOut(BaseModel):
    id: str
    source: str
    text: str
    coordinates: Optional[dict] = None
