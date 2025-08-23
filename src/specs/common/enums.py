from enum import Enum

class Platform(str, Enum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    X = "x"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"

class PostStatus(str, Enum):
    RETRIEVED = "retrieved brand & plan"
    COPYWRITER_COMPLETE = "copywriter complete"
    COMPOSER_COMPLETE = "composer complete"
    PUBLISHED = "published"

class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"