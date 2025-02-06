from datetime import datetime

import peewee

db = peewee.SqliteDatabase('feed_database.db')


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Post(BaseModel):
    # Core identifiers
    uri = peewee.CharField(index=True)
    cid = peewee.CharField()
    
    # Reply structure
    reply_parent = peewee.CharField(null=True, default=None)
    reply_root = peewee.CharField(null=True, default=None)
    
    # Metadata for filtering and ranking
    author = peewee.CharField()  # Store the DID of the author
    text = peewee.TextField()    # Full post text
    has_media = peewee.BooleanField(default=False)  # Images or videos
    
    # Timestamps
    created_at = peewee.DateTimeField()  # When the post was created
    indexed_at = peewee.DateTimeField(default=datetime.utcnow)  # When we indexed it
    
    # Ranking metrics
    like_count = peewee.IntegerField(default=0)  # For HN-style ranking
    repost_count = peewee.IntegerField(default=0)  # Additional engagement metric
    reply_count = peewee.IntegerField(default=0)   # Additional engagement metric
    score = peewee.FloatField(default=0.0)         # Computed HN-style score
    
    class Meta:
        # Add indexes for efficient querying
        indexes = (
            (('created_at', 'score'), False),  # Compound index for ranking queries
            (('author',), False),              # Index for author lookups
        )


class SubscriptionState(BaseModel):
    service = peewee.CharField(unique=True)
    cursor = peewee.BigIntegerField()


if db.is_closed():
    db.connect()
    db.create_tables([Post, SubscriptionState])