"""
Router de Autenticación – Paso 1
- Registro
- Login (email/username + password)
- Google Sign-In (estructura lista)
- Recuperación de contraseña con OTP 6 dígitos / 10 min
- Perfil básico del usuario autenticado
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from storage.database import get_db
from entities.user import User, PasswordOTP
from App.schemas.user import UserCreate, UserPublic, UserUpdate, Token
from App.schemas.auth import (
    LoginRequest,
    GoogleLoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from functions.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_otp_code,
    otp_expiration,
)
from functions.email_service import send_otp_email
from App.dependencies import get_current_user
from App.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Autenticación"])


# ---------- Helpers ----------

def _user_to_public(user: User) -> UserPublic:
    return UserPublic.model_validate(user)


def _create_token_response(user: User) -> Token:
    access_token = create_access_token(data={"sub": str(user.id), "username": user.username})
    return Token(access_token=access_token, user=_user_to_public(user))


# ---------- Registro ----------

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """
    Crea una cuenta nueva con correo + username + contraseña.
    Devuelve el JWT y los datos del usuario.
    """
    # Verificar unicidad
    existing = (
        db.query(User)
        .filter(or_(User.email == payload.email.lower(), User.username == payload.username.lower()))
        .first()
    )
    if existing:
        if existing.email == payload.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una cuenta con este correo electrónico",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está en uso",
        )

    # Determinar si es admin (lista en config)
    admin_emails = [e.strip().lower() for e in settings.ADMIN_EMAILS.split(",") if e.strip()]
    is_admin = payload.email.lower() in admin_emails

    user = User(
        email=payload.email.lower(),
        username=payload.username.lower(),
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        is_admin=is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _create_token_response(user)


# ---------- Login (correo o username) ----------

@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Inicia sesión con correo **o** nombre de usuario + contraseña.
    """
    identifier = payload.identifier.strip().lower()

    user = (
        db.query(User)
        .filter(or_(User.email == identifier, User.username == identifier))
        .first()
    )

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada. Contacta al administrador.",
        )

    return _create_token_response(user)


# ---------- Google Sign-In (estructura) ----------

@router.post("/google", response_model=Token)
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Recibe el id_token de Google (enviado por el cliente Android).
    Verifica el token con Google y crea o inicia sesión al usuario.

    Nota: para producción se debe verificar el token con la API de Google.
    Aquí dejamos la estructura lista; mientras tanto se puede probar con
    un flujo de desarrollo controlado.
    """
    # TODO: verificar id_token real con Google (httpx + tokeninfo o google-auth)
    # Por ahora devolvemos un error claro para no dejar un endpoint inseguro.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Google Sign-In está preparado en la arquitectura. "
            "Falta configurar GOOGLE_CLIENT_ID y la verificación del id_token. "
            "Usa registro/login con correo mientras tanto."
        ),
    )


# ---------- Recuperación de contraseña ----------

@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Genera un OTP de 6 dígitos, lo guarda (válido 10 min, un solo uso)
    y lo envía al correo. Por seguridad siempre responde el mismo mensaje.
    """
    email = payload.email.lower()
    user = db.query(User).filter(User.email == email).first()

    # Respuesta genérica para no revelar si el correo existe
    generic = MessageResponse(
        message="Si el correo está registrado, recibirás un código de 6 dígitos.",
        detail=f"El código expira en {settings.OTP_EXPIRE_MINUTES} minutos.",
    )

    if not user:
        return generic

    # Invalidar OTPs anteriores del mismo usuario
    db.query(PasswordOTP).filter(
        PasswordOTP.user_id == user.id,
        PasswordOTP.used == False,  # noqa: E712
    ).update({"used": True})

    code = generate_otp_code(6)
    otp = PasswordOTP(
        user_id=user.id,
        email=email,
        code=code,
        expires_at=otp_expiration(),
        used=False,
    )
    db.add(otp)
    db.commit()

    send_otp_email(to_email=email, code=code, username=user.username)

    return generic


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Verifica el OTP y establece la nueva contraseña.
    El código es de un solo uso.
    """
    email = payload.email.lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido o expirado",
        )

    otp = (
        db.query(PasswordOTP)
        .filter(
            PasswordOTP.user_id == user.id,
            PasswordOTP.email == email,
            PasswordOTP.code == payload.code,
            PasswordOTP.used == False,  # noqa: E712
        )
        .order_by(PasswordOTP.created_at.desc())
        .first()
    )

    if not otp or not otp.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido o expirado",
        )

    # Marcar como usado
    otp.used = True
    user.hashed_password = hash_password(payload.new_password)
    user.updated_at = datetime.now(timezone.utc)
    db.commit()

    return MessageResponse(
        message="Contraseña actualizada correctamente",
        detail="Ya puedes iniciar sesión con tu nueva contraseña.",
    )


# ---------- Usuario autenticado ----------

@router.get("/me", response_model=UserPublic)
def get_me(current_user: User = Depends(get_current_user)):
    """Devuelve el perfil del usuario autenticado."""
    return _user_to_public(current_user)


@router.put("/me", response_model=UserPublic)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualiza datos de perfil (nombre, bio, avatar, tema, color)."""
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(current_user, field, value)
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    return _user_to_public(current_user)
