from datetime import datetime
from typing import Optional

from server import config
from server.database import Post

uri = config.FEED_URI
CURSOR_EOF = 'eof'


def handler(cursor: Optional[str], limit: int) -> dict:
    # Get posts in reverse chronological order
    posts = (Post.select()
             .order_by(Post.created_at.desc())  # Changed to created_at for true chronological order
             .limit(limit))

    if cursor:
        if cursor == CURSOR_EOF:
            return {
                'cursor': CURSOR_EOF,
                'feed': []
            }
        cursor_parts = cursor.split('::')
        if len(cursor_parts) != 2:
            raise ValueError('Malformed cursor')

        created_at, cid = cursor_parts
        created_at = datetime.fromtimestamp(int(created_at) / 1000)
        # Updated to use created_at for cursor pagination
        posts = posts.where(
            ((Post.created_at == created_at) & (Post.cid < cid)) |
            (Post.created_at < created_at)
        )

    feed = [{'post': post.uri} for post in posts]

    cursor = CURSOR_EOF
    last_post = posts[-1] if posts else None
    if last_post:
        # Use created_at for cursor
        cursor = f'{int(last_post.created_at.timestamp() * 1000)}::{last_post.cid}'

    return {
        'cursor': cursor,
        'feed': feed
    }