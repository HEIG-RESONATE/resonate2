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
    points = mongoengine.DictField(null=True, blank=True)
    extra = mongoengine.DictField(null=True, blank=True)
    images = mongoengine.ListField(null=True, blank=True)
    news = mongoengine.ListField(mongoengine.EmbeddedDocumentField(NewsItem), null=True, blank=True)

    meta = {"collection": "events"}

    def __str__(self):
        return self.title
