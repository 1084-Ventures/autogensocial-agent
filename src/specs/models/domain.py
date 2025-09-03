from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    SecretStr,
)
try:
    # Pydantic v2 aware datetime
    from pydantic import AwareDatetime as DateTime
except Exception:  # pragma: no cover
    from datetime import datetime as DateTime  # type: ignore


class SocialPlatform(str, Enum):
    instagram = "instagram"
    facebook = "facebook"
    x = "x"  # formerly twitter
    tiktok = "tiktok"
    linkedin = "linkedin"
    youtube = "youtube"
    pinterest = "pinterest"


class PostContentType(str, Enum):
    image = "image"
    multi_image = "multi-image"
    video = "video"
    text = "text"


class ScheduleFrequency(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    CRON = "CRON"


class AccountCredentials(BaseModel):
    """Credentials/profile for a specific social platform account.

    accessToken is marked writeOnly in schema and treated as secret.
    Prefer storing tokens in a secure store and referencing them here only if necessary.
    """

    model_config = ConfigDict(extra="allow")

    platformAccountId: str = Field(alias="platform_account_id")
    handle: str
    username: str
    profileUrl: HttpUrl = Field(alias="profile_url")
    accessToken: Optional[SecretStr] = Field(
        default=None,
        alias="access_token",
        json_schema_extra={"writeOnly": True, "x-sensitive": True},
    )
    # Prefer a secret reference over storing tokens directly
    credentialRef: Optional[str] = Field(
        default=None,
        alias="credential_ref",
        json_schema_extra={"x-secret-ref": True},
    )
    expiryDate: Optional[DateTime] = Field(default=None, alias="expiry_date")
    extra: Optional[Dict[str, Any]] = None


class SocialAccountBinding(BaseModel):
    """Binding of a platform to its account credentials."""

    platform: SocialPlatform = Field(alias="platforms")
    account: AccountCredentials


HexColor = Field(
    pattern=r"^#(?:[0-9a-fA-F]{3}){1,2}$",
    description="CSS hex color, e.g. #RRGGBB or #RGB",
)


class BrandStyleColors(BaseModel):
    primary: str = HexColor
    secondary: Optional[str] = HexColor  # optional secondary
    accent1: Optional[str] = HexColor
    accent2: Optional[str] = HexColor
    accent3: Optional[str] = HexColor


class BrandStyleFonts(BaseModel):
    primary: str
    secondary: Optional[str] = None


class BrandStyle(BaseModel):
    description: Optional[str] = None
    colors: Optional[BrandStyleColors] = None
    fonts: Optional[BrandStyleFonts] = None
    # Additional guidance for copy generation (optional, non-prescriptive)
    voice: Optional[str] = None
    tone: Optional[List[str]] = None
    preferredHashtags: Optional[List[str]] = Field(default=None, alias="hashtags")
    emojiPolicy: Optional[Literal["allow", "avoid", "limited"]] = None


class BrandDocument(BaseModel):
    """Brand configuration document stored in the database.

    Uses camelCase field names with snake_case aliases for backward compatibility
    with earlier iterations.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    name: str
    description: Optional[str] = None
    logoUrl: Optional[HttpUrl] = Field(default=None, alias="logo_url")
    website: Optional[HttpUrl] = None
    socialAccounts: Optional[List[SocialAccountBinding]] = Field(
        default=None, alias="social_accounts"
    )
    brandStyle: Optional[BrandStyle] = Field(default=None, alias="brand_style")


class PostPlanInfo(BaseModel):
    name: str
    description: Optional[str] = None
    type: List[PostContentType]
    platforms: List[SocialPlatform]


class PostPlanSchedule(BaseModel):
    frequency: ScheduleFrequency
    startDate: DateTime = Field(alias="start_date")
    endDate: DateTime = Field(alias="end_date")
    timezone: Optional[str] = Field(default="UTC", description="IANA timezone, e.g. UTC")
    cron: Optional[str] = Field(
        default=None,
        description="Cron expression used when frequency=CRON",
    )


class PostPlanContent(BaseModel):
    topics: List[str]
    hashtags: List[str]


class PostPlanDefinition(BaseModel):
    info: PostPlanInfo
    schedule: PostPlanSchedule
    content: PostPlanContent


class PostExecutionStatus(str, Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ExecutionRecord(BaseModel):
    scheduledFor: Optional[DateTime] = None
    startedAt: Optional[DateTime] = None
    finishedAt: Optional[DateTime] = None
    status: Optional[PostExecutionStatus] = None
    instanceId: Optional[str] = None
    postRef: Optional[str] = Field(default=None, alias="post_ref")
    note: Optional[str] = None


class PostPlanStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class PostPlanDocument(BaseModel):
    """Plan defining what, when, and where to post for a brand."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    brandId: str = Field(alias="brand_id")
    plan: PostPlanDefinition = Field(alias="post_plan")
    status: PostPlanStatus
    lastExecutedAt: Optional[DateTime] = Field(default=None, alias="last_executed_at")
    executionHistory: List[ExecutionRecord] = Field(
        default_factory=list, alias="execution_history"
    )


__all__ = [
    "SocialPlatform",
    "PostContentType",
    "ScheduleFrequency",
    "AccountCredentials",
    "SocialAccountBinding",
    "BrandStyleColors",
    "BrandStyleFonts",
    "BrandStyle",
    "BrandDocument",
    "PostPlanInfo",
    "PostPlanSchedule",
    "PostPlanContent",
    "PostPlanDefinition",
    "PostExecutionStatus",
    "ExecutionRecord",
    "PostPlanStatus",
    "PostPlanDocument",
]
