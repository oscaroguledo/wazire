from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, List, Union
import re
from datetime import datetime, timezone
import uuid


class ValidationMixin(BaseModel):
    """Mixin with common validation methods."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    @field_validator('*')
    @classmethod
    def strip_strings(cls, v):
        """Strip whitespace from string fields."""
        if isinstance(v, str):
            return v.strip()
        return v


class EmailValidationMixin(BaseModel):
    """Mixin for email validation."""

    @field_validator('email', check_fields=False)
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        if not v:
            return v
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()


class PasswordValidationMixin(BaseModel):
    """Mixin for password validation."""

    @field_validator('password', check_fields=False)
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if not v:
            return v
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v


class SanitizeMixin(BaseModel):
    """Mixin for input sanitization."""

    @field_validator('*')
    @classmethod
    def sanitize_html(cls, v):
        """Basic HTML sanitization for string fields."""
        if isinstance(v, str):
            # Remove potentially dangerous HTML tags
            dangerous_tags = ['<script', '</script', '<iframe', '</iframe', '<object', '</object']
            for tag in dangerous_tags:
                if tag.lower() in v.lower():
                    raise ValueError(f'Invalid input: contains dangerous content')
        return v


def validate_uuid(uuid_str: str) -> bool:
    """Validate UUID format."""
    try:
        uuid.UUID(str(uuid_str))
        return True
    except (ValueError, AttributeError):
        return False


def validate_future_date(date: datetime) -> bool:
    """Validate that a date is in the future."""
    # Ensure both sides are timezone-aware in UTC before comparison.
    if date is None:
        return False
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    else:
        date = date.astimezone(timezone.utc)
    return date > datetime.now(timezone.utc)


def validate_positive_number(value: Union[int, float]) -> bool:
    """Validate that a number is positive."""
    return value > 0


def validate_duration(duration: int) -> bool:
    """Validate exam duration (in hours)."""
    return 0 < duration <= 24  # Max 24 hours


def validate_score(score: Union[int, float]) -> bool:
    """Validate score is between 0 and 100."""
    return 0 <= score <= 100


def validate_phone_number(phone: str) -> bool:
    """Validate phone number format (basic)."""
    if not phone:
        return True
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    # Check if it's 10-15 digits
    return bool(re.match(r'^\d{10,15}$', cleaned))
