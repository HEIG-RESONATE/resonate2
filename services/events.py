from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from models import Event, NewsItem
from schemas import EventOut


def is_valid_coordinate_pair(coord) -> bool:
    return (
        isinstance(coord, list)
        and len(coord) == 2
        and all(isinstance(v, (int, float)) for v in coord)
    )


def normalize_points(points) -> Optional[dict]:
    if not points:
        return None
    if hasattr(points, "model_dump"):
        points = points.model_dump()
    if isinstance(points, dict):
        coords = points.get("coordinates")
        if points.get("type") == "MultiPoint" and isinstance(coords, list) and all(is_valid_coordinate_pair(c) for c in coords):
            return {"type": "MultiPoint", "coordinates": coords}
        raise HTTPException(status_code=422, detail="points must be a GeoJSON MultiPoint object")
    if isinstance(points, list):
        if all(is_valid_coordinate_pair(c) for c in points):
            return {"type": "MultiPoint", "coordinates": points}
        raise HTTPException(status_code=422, detail="points must be a list of [lon, lat] numeric pairs")
    raise HTTPException(status_code=422, detail="points must be a GeoJSON MultiPoint object or a list of [lon, lat] pairs")


def format_points(points) -> Optional[dict]:
    if not points or not isinstance(points, dict):
        return None
    coords = points.get("coordinates")
    if points.get("type") == "MultiPoint" and isinstance(coords, list) and all(is_valid_coordinate_pair(c) for c in coords):
        return {"type": "MultiPoint", "coordinates": coords}
    return None


def format_news(news) -> Optional[list]:
    if not news:
        return None
    return [{"title": item.title, "url": item.url, "author": item.author, "extra": item.extra} for item in news]


def created_at(doc: Event) -> datetime:
    """Return a stable insertion timestamp, including for legacy documents."""
    value = doc.created_at
    if value is None:
        return doc.id.generation_time
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def timestamp(value: datetime) -> float:
    """Normalize naive legacy dates before using them as sort keys."""
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).timestamp()


def doc_to_event_out(doc: Event, *, is_latest: bool = False) -> EventOut:
    # Legacy and API-supplied image metadata is normalized on read so every
    # satellite image has an opaque ID before it is returned to a client.
    from services.images import ensure_image_ids

    return EventOut(
        id=str(doc.id),
        title=doc.title,
        date=doc.date.isoformat(),
        created_at=created_at(doc).isoformat(),
        is_latest=is_latest,
        points=format_points(doc.points),
        extra=doc.extra,
        images=ensure_image_ids(doc),
        carousel_images=doc.carousel_images,
        news=format_news(doc.news),
    )


def get_event_or_404(event_id: str) -> Event:
    doc = Event.objects(id=event_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


def list_events(sort_by: str = "date", direction: str = "desc") -> list[EventOut]:
    docs = list(Event.objects())
    if not docs:
        return []

    latest = max(docs, key=lambda doc: (timestamp(created_at(doc)), str(doc.id)))
    primary_key = (lambda doc: doc.date) if sort_by == "date" else created_at
    docs.sort(
        key=lambda doc: (timestamp(primary_key(doc)), timestamp(created_at(doc)), str(doc.id)),
        reverse=direction == "desc",
    )
    return [doc_to_event_out(doc, is_latest=doc.id == latest.id) for doc in docs]


def get_event(event_id: str) -> EventOut:
    doc = get_event_or_404(event_id)
    return doc_to_event_out(doc)


def create_event(title: str, date: str, points=None, extra=None, images=None, carousel_images=None, news=None) -> EventOut:
    parsed_date = datetime.fromisoformat(date)
    normalized_points = normalize_points(points)

    news_items = None
    if news:
        news_items = [NewsItem(title=n["title"], url=n.get("url"), author=n.get("author"), extra=n.get("extra")) for n in news]

    doc = Event(
        title=title,
        date=parsed_date,
        created_at=datetime.now(timezone.utc),
        points=normalized_points,
        extra=extra,
        images=images or [],
        carousel_images=carousel_images or [],
        news=news_items or [],
    )
    doc.save()
    return doc_to_event_out(doc)


def update_event(event_id: str, **updates) -> EventOut:
    doc = get_event_or_404(event_id)

    if "title" in updates:
        if updates["title"] is None:
            raise HTTPException(status_code=422, detail="title cannot be null")
        doc.title = updates["title"]
    if "date" in updates:
        if updates["date"] is None:
            raise HTTPException(status_code=422, detail="date cannot be null")
        doc.date = datetime.fromisoformat(updates["date"])
    if "points" in updates:
        doc.points = normalize_points(updates["points"])
    if "extra" in updates:
        doc.extra = updates["extra"]
    if "images" in updates:
        doc.images = updates["images"]
    if "carousel_images" in updates:
        doc.carousel_images = updates["carousel_images"]
    if "news" in updates:
        news = updates["news"]
        doc.news = [NewsItem(title=n["title"], url=n.get("url"), author=n.get("author"), extra=n.get("extra")) for n in news] if news is not None else []

    doc.save()

    return doc_to_event_out(doc)


def delete_event(event_id: str) -> None:
    doc = get_event_or_404(event_id)
    doc.delete()
