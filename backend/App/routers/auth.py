"""
Router de Autenticación – Paso 1
- Registro
- Login (email/username + password)
- Google Sign-In (estructura lista)
- Recuperación de contraseña con OTP 6 dígitos / 10 min
- Perfil básico del usuario autenticado
"""
import secrets

from sqlalchemy.exc import IntegrityError
from functions.supabase_auth import verify_supabase_google_token

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


# ---------- Google Sign-In ----------

@router.post("/google", response_model=Token)
def google_login(
    payload: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Registro o inicio de sesión mediante Google + Supabase Auth.

    No modifica cuentas existentes únicamente por coincidencia
    de correo electrónico.
    """

    identity = verify_supabase_google_token(
        payload.access_token
    )

    google_id = identity["google_id"]
    email = identity["email"]
    display_name = identity["display_name"]

    # 1. Buscar una cuenta ya vinculada con Google.
    user = (
        db.query(User)
        .filter(User.google_id == google_id)
        .first()
    )

    if user:
        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="Cuenta desactivada",
            )

        return _create_token_response(user)

    # 2. Comprobar conflictos con cuentas existentes.
    existing_email = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=409,
            detail=(
                "Ya existe una cuenta de PicRout con este correo. "
                "Inicia sesión mediante tu método habitual. "
                "La vinculación de Google deberá autorizarse "
                "desde esa cuenta."
            ),
        )

    # 3. Generar un username único.
    # Nunca utilizamos el correo como identificador público.
    username = ""

    for _ in range(10):
        candidate = "google_" + secrets.token_hex(8)

        exists = (
            db.query(User)
            .filter(User.username == candidate)
            .first()
        )

        if not exists:
            username = candidate
            break

    if not username:
        raise HTTPException(
            status_code=503,
            detail="No se pudo generar un nombre de usuario",
        )

    # 4. Crear el usuario de PicRout.
    # Sin contraseña local: se autenticará mediante Google.
    user = User(
        email=email,
        username=username,
        display_name=display_name,
        google_id=google_id,
        hashed_password=None,
        is_admin=False,
        is_active=True,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "Conflicto al crear la cuenta. "
                "Comprueba si ya existe e inténtalo de nuevo."
            ),
        )

    # 5. Entregar el JWT habitual de PicRout.
    return _create_token_response(user)



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
