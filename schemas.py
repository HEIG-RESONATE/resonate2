import json
from typing import Any, Optional, List, Union
from pydantic import BaseModel, field_validator


class NewsItem(BaseModel):
    title: str
    url: Optional[str] = None
    author: Optional[str] = None
    extra: Optional[dict] = None

    @field_validator("extra")
    @classmethod
    def validate_extra_size(cls, v):
        if v is not None and len(json.dumps(v)) > 65536:
            raise ValueError("extra field exceeds 64KB limit")
        return v


class CarouselImage(BaseModel):
    url: str
    source_url: Optional[str] = None
    description: Optional[str] = None


class GeoJSONMultiPoint(BaseModel):
    type: str
    coordinates: List[List[float]]

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v != "MultiPoint":
            raise ValueError("points.type must be 'MultiPoint'")
        return v

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v):
        for coord in v:
            if len(coord) != 2:
                raise ValueError("each coordinate must contain exactly two numeric values: [lon, lat]")
        return v


class EventCreate(BaseModel):
    title: str
    date: str
    points: Optional[Union[List[List[float]], GeoJSONMultiPoint]] = None
    extra: Optional[dict] = None
    images: Optional[list] = None
    carousel_images: Optional[List[CarouselImage]] = None
    news: Optional[List[NewsItem]] = None

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
    created_at: str
    is_latest: bool = False
    points: Optional[GeoJSONMultiPoint] = None
    extra: Optional[dict] = None
    images: Optional[list] = None
    carousel_images: Optional[List[CarouselImage]] = None
    news: Optional[List[NewsItem]] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    points: Optional[Union[List[List[float]], GeoJSONMultiPoint]] = None
    extra: Optional[dict[str, Any]] = None
    images: Optional[list] = None
    carousel_images: Optional[List[CarouselImage]] = None
    news: Optional[List[NewsItem]] = None

    @field_validator("extra")
    @classmethod
    def validate_extra_size(cls, v):
        if v is not None and len(json.dumps(v)) > 65536:
            raise ValueError("extra field exceeds 64KB limit")
        return v


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
