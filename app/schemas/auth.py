from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Schema for login credentials."""

    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """Schema for successful authentication response containing JWT tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Schema for initiating a password reset."""

    email: EmailStr = Field(..., max_length=255)


class PasswordResetConfirmRequest(BaseModel):
    """Schema for confirming a password reset with a new password."""

    email: EmailStr = Field(..., max_length=255)
    token: str = Field(..., min_length=32)
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        from app.schemas.user import PASSWORD_REGEX

        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "New password must be at least 8 characters long and contain at "
                "least one uppercase letter, one lowercase letter, one digit, "
                "and one special character (@$!%*?&)."
            )
        return v
