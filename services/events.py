from datetime import datetime
from typing import Optional

from fastapi import HTTPException

from models import Event, NewsItem
from schemas import EventOut


def normalize_points(points) -> Optional[dict]:
    if not points:
        return None
    if isinstance(points, list):
        return {"type": "MultiPoint", "coordinates": points}
    return points


def format_points(points) -> Optional[dict]:
    if not points or not isinstance(points, dict):
        return None
    coords = points.get("coordinates")
    if coords and isinstance(coords, list):
        return {"type": "MultiPoint", "coordinates": coords}
    return None


def format_news(news) -> Optional[list]:
    if not news:
        return None
    return [{"title": item.title, "url": item.url, "author": item.author, "extra": item.extra} for item in news]


def doc_to_event_out(doc: Event) -> EventOut:
    return EventOut(
        id=str(doc.id),
        title=doc.title,
        date=doc.date.isoformat(),
        points=format_points(doc.points),
        extra=doc.extra,
        images=doc.images,
        news=format_news(doc.news),
    )


def get_event_or_404(event_id: str) -> Event:
    doc = Event.objects(id=event_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


def list_events() -> list[EventOut]:
    docs = Event.objects().order_by("-date")
    return [doc_to_event_out(doc) for doc in docs]


def get_event(event_id: str) -> EventOut:
    doc = get_event_or_404(event_id)
    return doc_to_event_out(doc)


def create_event(title: str, date: str, points=None, extra=None, images=None, news=None) -> EventOut:
    parsed_date = datetime.fromisoformat(date)
    normalized_points = normalize_points(points)

    news_items = None
    if news:
        news_items = [NewsItem(title=n["title"], url=n.get("url"), author=n.get("author"), extra=n.get("extra")) for n in news]

    doc = Event(
        title=title,
        date=parsed_date,
        points=normalized_points,
        extra=extra,
        images=images or [],
        news=news_items or [],
    )
    doc.save()
    return doc_to_event_out(doc)


def update_event(event_id: str, title: str, date: str, points=None, extra=None, images=None, news=None) -> EventOut:
    doc = get_event_or_404(event_id)
    parsed_date = datetime.fromisoformat(date)
    normalized_points = normalize_points(points)

    doc.title = title
    doc.date = parsed_date
    doc.points = normalized_points
    doc.extra = extra
    if images is not None:
        doc.images = images
    if news is not None:
        doc.news = [NewsItem(title=n["title"], url=n.get("url"), author=n.get("author"), extra=n.get("extra")) for n in news]
    doc.save()

    return doc_to_event_out(doc)


def delete_event(event_id: str) -> None:
    doc = get_event_or_404(event_id)
    doc.delete()
