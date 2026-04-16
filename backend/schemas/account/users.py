from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from core.utils.validation import ValidationMixin, EmailValidationMixin, PasswordValidationMixin


class UserBase(ValidationMixin, EmailValidationMixin):
    model_config = ConfigDict(from_attributes=True)
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    email: str
    institution_id: Optional[str] = None  # Matric number / Reg No

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v):
        """Validate name fields."""
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        if len(v) > 50:
            raise ValueError('Name must not exceed 50 characters')
        return v

    @field_validator('institution_id')
    @classmethod
    def validate_institution_id(cls, v):
        """Validate institution ID."""
        if v is not None:
            if len(v.strip()) < 3:
                raise ValueError('Institution ID must be at least 3 characters long')
            if len(v) > 50:
                raise ValueError('Institution ID must not exceed 50 characters')
        return v


class UserCreate(UserBase, PasswordValidationMixin):
    password: str
    role: Optional[str] = "student"
    tenant_id: Optional[UUID] = None
    institution_id: Optional[str] = None  # Matric number / Reg No

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        """Validate user role."""
        if v is not None:
            valid_roles = ['student', 'lecturer', 'admin', 'superadmin']
            if v.lower() not in valid_roles:
                raise ValueError(f'Invalid role. Must be one of: {", ".join(valid_roles)}')
        return v


class UserUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    institution_id: Optional[str] = None  # Matric number / Reg No

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v):
        """Validate name fields."""
        if v is not None:
            if len(v.strip()) < 2:
                raise ValueError('Name must be at least 2 characters long')
            if len(v) > 50:
                raise ValueError('Name must not exceed 50 characters')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if v is not None:
            if len(v) < 8:
                raise ValueError('Password must be at least 8 characters long')
        return v


class UserRead(UserBase):
    id: UUID
    role: str
    is_active: bool
    tenant_id: Optional[UUID]
    tenant_name: Optional[str] = None
    logo_url: Optional[str] = None
    institution_id: Optional[str] = None  # Matric number / Reg No
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @field_validator('role', mode='before')
    @classmethod
    def normalize_role(cls, v):
        """Normalize role to lowercase string regardless of enum or string input."""
        if hasattr(v, 'value'):
            return v.value.lower()
        return str(v).lower()

    @model_validator(mode='before')
    @classmethod
    def extract_tenant_info(cls, data):
        """Extract tenant_name and logo_url from tenant relationship."""
        if hasattr(data, 'tenant') and data.tenant:
            data.tenant_name = data.tenant.name
            data.logo_url = data.tenant.logo_url
        return data
