from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import AnyUrl, BaseModel, Field, HttpUrl, constr


HexColor = constr(pattern=r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")


class Metadata(BaseModel):
    version: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    owner_email: Optional[str] = None


class Fonts(BaseModel):
    primary: Optional[str] = None
    secondary: Optional[str] = None


class Tone(BaseModel):
    voice: Optional[str] = None
    personality: List[str] = Field(default_factory=list)
    do: List[str] = Field(default_factory=list)
    dont: List[str] = Field(default_factory=list)


class Imagery(BaseModel):
    guidelines: Optional[str] = None
    aspect_ratios: List[str] = Field(default_factory=list)


class StyleColors(BaseModel):
    primary: Optional[HexColor] = None
    secondary: Optional[HexColor] = None
    # Allow extra named colors like accent1, accent2, etc.
    __root__: Dict[str, HexColor] | None = None  # backwards-compatible flex field


class StyleGuide(BaseModel):
    description: str
    colors: Dict[str, HexColor] | StyleColors
    fonts: Fonts
    tone: Optional[Tone] = None
    imagery: Optional[Imagery] = None


class Connection(BaseModel):
    secret_ref: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: List[str] = Field(default_factory=list)


class SocialAccountDetails(BaseModel):
    platform_account_id: str
    handle: str
    username: str
    profile_url: HttpUrl
    status: Optional[Literal["active", "inactive"]] = "active"
    connection: Optional[Connection] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class SocialAccount(BaseModel):
    platform: Literal[
        "instagram",
        "facebook",
        "x",
        "tiktok",
        "linkedin",
        "youtube",
        "pinterest",
    ]
    account: SocialAccountDetails


class Pillar(BaseModel):
    name: str
    description: Optional[str] = None


class ContentStrategy(BaseModel):
    audience: Optional[str] = None
    personas: List[str] = Field(default_factory=list)
    pillars: List[Pillar] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    default_hashtags: List[str] = Field(default_factory=list)
    prohibited_topics: List[str] = Field(default_factory=list)
    disclaimers: List[str] = Field(default_factory=list)


class Cadence(BaseModel):
    posts_per_week: Optional[int] = Field(default=None, ge=0)


class PublishingPreferences(BaseModel):
    timezone: Optional[str] = None
    cadence: Optional[Cadence] = None
    best_times: Dict[str, List[str]] = Field(default_factory=dict)
    default_caption_template: Optional[str] = None
    default_cta: Optional[str] = None


class UTMParams(BaseModel):
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


class LinkShortening(BaseModel):
    provider: Optional[str] = None
    enabled: bool = False


class Analytics(BaseModel):
    utm_defaults: Dict[str, UTMParams] = Field(default_factory=dict)
    link_shortening: Optional[LinkShortening] = None


class StorageQueues(BaseModel):
    content_tasks: Optional[str] = None
    media_tasks: Optional[str] = None
    publish_tasks: Optional[str] = None


class AzureIntegrations(BaseModel):
    storage_queues: Optional[StorageQueues] = None


class Integrations(BaseModel):
    azure: Optional[AzureIntegrations] = None


class Compliance(BaseModel):
    privacy_policy_url: Optional[AnyUrl] = None
    medical_disclaimer: Optional[str] = None
    moderation_policy: Optional[str] = None


class Brand(BaseModel):
    # Cosmos identity & partitioning helpers
    id: str
    brandId: Optional[str] = None
    partitionKey: Optional[str] = None

    # Basics
    name: str
    description: str
    status: Literal["active", "inactive"] = "active"
    website: Optional[AnyUrl] = None
    logo_url: Optional[AnyUrl] = None

    # Specified sections
    metadata: Optional[Metadata] = None
    style_guide: StyleGuide
    social_accounts: List[SocialAccount]

    # Optional strategy & ops
    content_strategy: Optional[ContentStrategy] = None
    publishing_preferences: Optional[PublishingPreferences] = None
    analytics: Optional[Analytics] = None
    integrations: Optional[Integrations] = None
    compliance: Optional[Compliance] = None

    class Config:
        extra = "allow"  # tolerate legacy fields (e.g., brand_style alias)


def normalize_brand_ids(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure id/brandId/partitionKey are aligned for Cosmos reads.

    This keeps compatibility with containers partitioned on /id, /brandId or /partitionKey.
    """
    brand_id = doc.get("id") or doc.get("brandId") or doc.get("partitionKey")
    if brand_id:
        doc.setdefault("id", brand_id)
        doc.setdefault("brandId", brand_id)
        doc.setdefault("partitionKey", brand_id)
    return doc


def parse_brand(doc: Dict[str, Any]) -> Brand:
    """Parse and validate a raw brand document dict into Brand model.

    Also maps legacy field 'brand_style' -> 'style_guide' for backwards compatibility.
    """
    if "style_guide" not in doc and "brand_style" in doc:
        doc = {**doc, "style_guide": doc["brand_style"]}
    doc = normalize_brand_ids(dict(doc))
    return Brand.model_validate(doc)

