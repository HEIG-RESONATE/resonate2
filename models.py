from datetime import datetime, timezone
from typing import Optional
import mongoengine


class NewsItem(mongoengine.EmbeddedDocument):
    title = mongoengine.StringField(required=True)
    url = mongoengine.StringField(null=True, blank=True)
    author = mongoengine.StringField(null=True, blank=True)
    extra = mongoengine.DictField(null=True, blank=True)


class Event(mongoengine.Document):
    title = mongoengine.StringField(required=True)
    date = mongoengine.DateTimeField(required=True)
    created_at = mongoengine.DateTimeField(required=True, default=lambda: datetime.now(timezone.utc))
    points = mongoengine.DictField(null=True, blank=True)
    extra = mongoengine.DictField(null=True, blank=True)
    images = mongoengine.ListField(null=True, blank=True)
    carousel_images = mongoengine.ListField(null=True, blank=True)
    news = mongoengine.ListField(mongoengine.EmbeddedDocumentField(NewsItem), null=True, blank=True)

    meta = {"collection": "events"}

    def __str__(self):
        return self.title


def backfill_legacy_created_at() -> None:
    """Assign ObjectId creation times to events created before ``created_at`` existed."""
    collection = Event._get_collection()
    for legacy in collection.find({"created_at": {"$exists": False}}, {"_id": 1}):
        collection.update_one(
            {"_id": legacy["_id"], "created_at": {"$exists": False}},
            {"$set": {"created_at": legacy["_id"].generation_time}},
        )
