"""
Schemas de Usuario (Pydantic).
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def username_format(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError("El username solo puede contener letras minúsculas, números y _")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class UserUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=100)
    bio: str | None = Field(None, max_length=500)
    avatar_url: str | None = None
    theme: str | None = Field(None, pattern="^(system|light|dark)$")
    color: str | None = Field(None, max_length=20)


class UserPublic(BaseModel):
    """Respuesta pública / para el cliente (sin datos sensibles)."""

    id: int
    email: EmailStr
    username: str
    display_name: str
    avatar_url: str | None = None
    bio: str | None = None
    theme: str = "system"
    color: str = "#4F46E5"
    points: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    is_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class TokenData(BaseModel):
    user_id: int | None = None
    username: str | None = None
