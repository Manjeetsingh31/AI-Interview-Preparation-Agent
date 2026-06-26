from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Shared fields used across create, update, and response schemas.

    Using EmailStr from pydantic for automatic email format validation.
    full_name is optional to support minimal registration flows.
    """
    full_name: Optional[str] = Field(None, max_length=255, description="User's display name")
    email: EmailStr = Field(..., description="Primary login email — must be unique")


class UserCreate(UserBase):
    """Schema for user registration requests.

    password is required (min 6 chars) and is NEVER returned in responses.
    The service layer hashes it before storing.
    """
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Plain-text password (will be hashed before storage)",
    )


class UserUpdate(BaseModel):
    """Schema for partial user profile updates.

    All fields are optional so callers can send only the changed fields.
    """
    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, max_length=128)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user data returned to clients.

    Uses model_config with from_attributes=True (Pydantic v2) to enable
    ORM-to-schema conversion without manual field mapping.
    """
    id: str = Field(..., description="UUID v4 primary key")
    is_active: bool = Field(True, description="Whether the account is enabled")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last profile update timestamp")

    model_config = {"from_attributes": True}
