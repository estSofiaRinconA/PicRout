"""
Schemas específicos de autenticación.
"""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login con correo o username + contraseña."""

    identifier: str = Field(..., description="Correo electrónico o nombre de usuario")
    password: str


class GoogleLoginRequest(BaseModel):
    """
    El cliente Android envía el id_token de Google.
    El backend lo verifica con Google y crea/inicia sesión.
    """

    id_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(..., min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None
