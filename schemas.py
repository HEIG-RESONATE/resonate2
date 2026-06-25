import json
from typing import Optional, List, Union
from pydantic import BaseModel, field_validator


class EventCreate(BaseModel):
    title: str
    date: str
    points: Optional[Union[list, dict]] = None
    extra: Optional[dict] = None
    images: Optional[list] = None

    @field_validator("extra")
    @classmethod
    def validate_extra_size(cls, v):
        if v is not None and len(json.dumps(v)) > 65536:
            raise ValueError("extra field exceeds 64KB limit")
        return v


class EventOut(BaseModel):
    id: str
    title: str
    date: str
    points: Optional[Union[list, dict]] = None
    extra: Optional[dict] = None
    images: Optional[list] = None


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
