from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List, Dict, Any, Literal, get_args
from ..common.constants import SOCIAL_PLATFORMS
from ..common.base_document_spec import BaseDocument

class PlatformAccount(BaseModel):
    platform_account_id: str
    handle: Optional[str] = None
    username: Optional[str] = None
    profile_url: Optional[HttpUrl] = None
    access_token: str
    expiry_date: Optional[str] = None  # ISO date string
    extra: Optional[Dict[str, Any]] = None

class SocialAccount(BaseModel):
    platforms: List[str]
    account: PlatformAccount

    @field_validator("platforms", mode="before")
    @classmethod
    def validate_platforms(cls, values):
        for value in values:
            if value not in SOCIAL_PLATFORMS:
                raise ValueError(f"Each platform must be one of {SOCIAL_PLATFORMS}, got '{value}'")
        return values

class BrandColors(BaseModel):
    primary: Optional[str] = None
    secondary: Optional[str] = None
    accent1: Optional[str] = None
    accent2: Optional[str] = None
    accent3: Optional[str] = None

class BrandFonts(BaseModel):
    primary: Optional[str] = None
    secondary: Optional[str] = None

class BrandStyle(BaseModel):
    colors: Optional[BrandColors] = None
    fonts: Optional[BrandFonts] = None

class BrandDocument(BaseDocument):
    name: str
    description: str
    logo_url: Optional[HttpUrl] = None
    website: Optional[HttpUrl] = None
    social_accounts: Optional[List[SocialAccount]] = None
    brand_style: Optional[BrandStyle] = None