import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: Optional[str] = Field(default=None, max_length=50)
    color: Optional[str] = Field(default=None, max_length=7)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.startswith("#") or len(v) != 7:
                raise ValueError(
                    "Color must be a valid hex color code starting with # (e.g. #FF5733)"
                )
        return v


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    icon: Optional[str] = Field(default=None, max_length=50)
    color: Optional[str] = Field(default=None, max_length=7)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.startswith("#") or len(v) != 7:
                raise ValueError(
                    "Color must be a valid hex color code starting with # (e.g. #FF5733)"
                )
        return v


class CategoryResponse(CategoryBase):
    id: uuid.UUID
    is_system: bool
    user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {uuid.UUID: lambda v: str(v)}
