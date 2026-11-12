
"""
Schemas específicos de autenticación de PicRout.
"""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login tradicional con correo o username."""

    identifier: str = Field(
        ...,
        description="Correo electrónico o nombre de usuario"
    )
    password: str


class GoogleLoginRequest(BaseModel):
    """
    Inicio de sesión mediante Google y Supabase Auth.
    """

    access_token: str = Field(
        ...,
        min_length=1,
        description="Access token de Supabase Auth"
    )


class ForgotPasswordRequest(BaseModel):
    """Solicitar recuperación de contraseña."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Restablecer contraseña mediante código OTP."""

    email: EmailStr
    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128
    )


class MessageResponse(BaseModel):
    """Respuesta informativa de la API."""

    message: str
    detail: str | None = None
