from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List, Dict, Any, Literal, get_args
from ..common.enums import Platform
from ..common.base_document_spec import BaseDocument


class PlatformAccount(BaseModel):
    platform_account_id: str # Unique identifier for the platform account
    handle: Optional[str] = None # Handle for the social media account
    username: Optional[str] = None # Username for the social media account
    profile_url: Optional[HttpUrl] = None # Profile URL for the social media account
    access_token: str # Access token for the social media account
    expiry_date: Optional[str] = None  # ISO date string
    extra: Optional[Dict[str, Any]] = None # Additional metadata for the platform account


class SocialAccount(BaseModel):
    platforms: Platform # Platform the account is associated with
    account: PlatformAccount # Platform account details


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
    description: Optional[str] = None # Description of the brand style
    colors: Optional[BrandColors] = None
    fonts: Optional[BrandFonts] = None

class BrandDocument(BaseDocument):
    name: str
    description: str
    logo_url: Optional[HttpUrl] = None
    website: Optional[HttpUrl] = None
    social_accounts: Optional[List[SocialAccount]] = None
    brand_style: Optional[BrandStyle] = None