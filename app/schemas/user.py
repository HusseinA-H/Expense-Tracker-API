import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

# 1 uppercase, 1 lowercase, 1 digit, 1 special character, min 8 characters
PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)
# Letters and spaces only
NAME_REGEX = re.compile(r"^[A-Za-z\s]+$")


class UserBase(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    preferred_currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v: str) -> str:
        if not NAME_REGEX.match(v):
            raise ValueError("Name must contain only alphabetic characters and spaces")
        return v

    @field_validator("preferred_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v_upper = v.upper()
        if not v_upper.isalpha():
            raise ValueError("Preferred currency must contain only letters")
        return v_upper


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must be at least 8 characters long and contain at "
                "least one uppercase letter, one lowercase letter, one digit, "
                "and one special character (@$!%*?&)."
            )
        return v


class UserUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    preferred_currency: str | None = Field(default=None, min_length=3, max_length=3)

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v: str | None) -> str | None:
        if v is not None and not NAME_REGEX.match(v):
            raise ValueError("Name must contain only alphabetic characters and spaces")
        return v

    @field_validator("preferred_currency")
    @classmethod
    def validate_currency(cls, v: str | None) -> str | None:
        if v is not None:
            v_upper = v.upper()
            if not v_upper.isalpha():
                raise ValueError("Preferred currency must contain only letters")
            return v_upper
        return v


class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    is_verified: bool
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "New password must be at least 8 characters long and contain at "
                "least one uppercase letter, one lowercase letter, one digit, "
                "and one special character (@$!%*?&)."
            )
        return v
