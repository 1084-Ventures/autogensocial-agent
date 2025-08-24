"""
Common exception classes for the application
"""
from typing import Optional, Dict, Any

class AutogenSocialError(Exception):
    """Base exception class for AutogenSocial errors"""
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to standard error format"""
        return {
            "code": self.code,
            "message": str(self),
            "details": self.details
        }

class ConfigurationError(AutogenSocialError):
    """Raised when there's an error in configuration or environment variables"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="CONFIGURATION_ERROR", details=details)

class ToolError(AutogenSocialError):
    """Raised when a tool operation fails"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="TOOL_ERROR", details=details)

class ContentGenerationError(AutogenSocialError):
    """Raised when content generation fails"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="CONTENT_GENERATION_ERROR", details=details)

class MediaGenerationError(AutogenSocialError):
    """Raised when media generation fails"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="MEDIA_GENERATION_ERROR", details=details)

class PublishError(AutogenSocialError):
    """Raised when publishing fails"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="PUBLISH_ERROR", details=details)

class ResourceNotFoundError(AutogenSocialError):
    """Raised when a requested resource is not found"""
    def __init__(self, resource_type: str, resource_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(message, code="RESOURCE_NOT_FOUND", details=details)
