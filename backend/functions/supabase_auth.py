
"""
PicRout - Validación de Google Sign-In mediante Supabase Auth.

Verifica el access_token con Supabase antes de aceptar
la identidad del usuario.
"""

import httpx
from fastapi import HTTPException

from App.config import get_settings

settings = get_settings()


def verify_supabase_google_token(access_token: str) -> dict:
    """
    Valida una sesión de Supabase Auth y comprueba
    que contiene una identidad Google verificada.
    """

    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=503,
            detail="Supabase Auth no está configurado",
        )

    if not access_token or len(access_token) > 8192:
        raise HTTPException(
            status_code=401,
            detail="Token inválido",
        )

    url = (
        settings.SUPABASE_URL.rstrip("/")
        + "/auth/v1/user"
    )

    try:
        response = httpx.get(
            url,
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {access_token}",
            },
            timeout=10.0,
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar con Supabase Auth",
        )

    if response.status_code in (401, 403):
        raise HTTPException(
            status_code=401,
            detail="Sesión inválida o expirada",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=503,
            detail="Error al validar la sesión",
        )

    try:
        user = response.json()
    except ValueError:
        raise HTTPException(
            status_code=503,
            detail="Respuesta inválida de Supabase",
        )

    if not isinstance(user, dict) or not user.get("id"):
        raise HTTPException(
            status_code=401,
            detail="Usuario de Supabase inválido",
        )

    # Buscar una identidad de Google vinculada.
    identities = user.get("identities") or []

    google_identity = next(
        (
            identity
            for identity in identities
            if isinstance(identity, dict)
            and identity.get("provider") == "google"
        ),
        None,
    )

    if not google_identity:
        raise HTTPException(
            status_code=403,
            detail="No existe una identidad Google vinculada",
        )

    identity_data = (
        google_identity.get("identity_data") or {}
    )

    if not isinstance(identity_data, dict):
        raise HTTPException(
            status_code=403,
            detail="Datos de identidad Google inválidos",
        )

    # El identificador puede aparecer en cualquiera
    # de estos dos campos, según la respuesta.
    google_id = str(
        google_identity.get("provider_id")
        or identity_data.get("sub")
        or ""
    ).strip()

    email = str(user.get("email") or "").strip().lower()

    google_email = str(
        identity_data.get("email") or ""
    ).strip().lower()

    # No basta con tener una sesión válida:
    # Google debe haber verificado el correo.
    email_verified = (
        identity_data.get("email_verified") is True
    )

    # Confirmación del correo en Supabase.
    supabase_confirmed = bool(
        user.get("email_confirmed_at")
        or user.get("confirmed_at")
    )

    if not google_id:
        raise HTTPException(
            status_code=403,
            detail="Identificador Google no disponible",
        )

    if not email or not google_email:
        raise HTTPException(
            status_code=403,
            detail="Correo de Google no disponible",
        )

    if email != google_email:
        raise HTTPException(
            status_code=403,
            detail="El correo de Google no coincide con la sesión",
        )

    if not email_verified:
        raise HTTPException(
            status_code=403,
            detail="Google no ha confirmado el correo",
        )

    if not supabase_confirmed:
        raise HTTPException(
            status_code=403,
            detail="Supabase no ha confirmado el correo",
        )

    metadata = user.get("user_metadata") or {}

    display_name = (
        identity_data.get("full_name")
        or metadata.get("full_name")
        or email.split("@")[0]
    )

    return {
        "google_id": google_id,
        "email": email,
        "display_name": str(display_name)[:100],
    }
