import datetime
from collections import defaultdict
from atproto import models
from server import config
from server.logger import logger
from server.database import db, Post

# Define Finger Lakes region keywords
FLX_KEYWORDS = {
    'ithaca', 'tompkins', '14850', 'flxsky', 'cornell', 'ithacany', 
    'fingerlakes', 'cayuga', 'trumansburg'
}

# Add any specific users to always include (replace with actual DIDs)
ALWAYS_INCLUDE_USERS = {
    'did:plc:oynycxf3neiejuf272tswm5n', # Ithaca Voice
    'did:plc:wekkzymalzgyxlboce5ezecm' # Ithaca Murals
}

def is_archive_post(record: 'models.AppBskyFeedPost.Record') -> bool:
    archived_threshold = datetime.timedelta(days=1)
    created_at = datetime.datetime.fromisoformat(record.created_at)
    now = datetime.datetime.now(datetime.UTC)
    return now - created_at > archived_threshold

def should_ignore_post(record: 'models.AppBskyFeedPost.Record') -> bool:
    if config.IGNORE_ARCHIVED_POSTS and is_archive_post(record):
        logger.debug(f'Ignoring archived post: {record.uri}')
        return True
    
    # Note: We're not ignoring replies as per requirements
    return False

def is_flx_relevant(text: str, author: str) -> bool:
    """Check if post is relevant to Finger Lakes region."""
    # Check if author is in our always-include list
    if author in ALWAYS_INCLUDE_USERS:
        return True
    
    # Convert text to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Check for any of our keywords
    for keyword in FLX_KEYWORDS:
        if keyword in text_lower:
            return True
    
    return False

def operations_callback(ops: defaultdict) -> None:
    posts_to_create = []
    for created_post in ops[models.ids.AppBskyFeedPost]['created']:
        author = created_post['author']
        record = created_post['record']

        post_with_images = isinstance(record.embed, models.AppBskyEmbedImages.Main)
        post_with_video = isinstance(record.embed, models.AppBskyEmbedVideo.Main)
        inlined_text = record.text.replace('\n', ' ')

        # Log all posts for debugging
        logger.debug(
            f'NEW POST '
            f'[CREATED_AT={record.created_at}]'
            f'[AUTHOR={author}]'
            f'[WITH_IMAGE={post_with_images}]'
            f'[WITH_VIDEO={post_with_video}]'
            f': {inlined_text}'
        )

        if should_ignore_post(record):
            continue

        # Check if post is relevant to Finger Lakes region
        if is_flx_relevant(record.text, author):
            # Get reply information if it exists
            reply_root = reply_parent = None
            if record.reply:
                reply_root = record.reply.root.uri
                reply_parent = record.reply.parent.uri

            # Store additional metadata for ranking
            post_dict = {
                'uri': created_post['uri'],
                'cid': created_post['cid'],
                'reply_parent': reply_parent,
                'reply_root': reply_root,
                'indexed_at': datetime.datetime.now(datetime.UTC),
                'text': record.text,  # Store text for potential re-filtering
                'has_media': post_with_images or post_with_video,
                'author': author,
            }
            posts_to_create.append(post_dict)

    # Handle deleted posts
    posts_to_delete = ops[models.ids.AppBskyFeedPost]['deleted']
    if posts_to_delete:
        post_uris_to_delete = [post['uri'] for post in posts_to_delete]
        Post.delete().where(Post.uri.in_(post_uris_to_delete))
        logger.debug(f'Deleted from feed: {len(post_uris_to_delete)}')

    # Create new posts
    if posts_to_create:
        with db.atomic():
            for post_dict in posts_to_create:
                Post.create(**post_dict)
        logger.debug(f'Added to feed: {len(posts_to_create)}')