"""
Utilidades para guardar fotos de evidencia de forma segura.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile, HTTPException, status

from App.config import get_settings

settings = get_settings()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
EXT_BY_CONTENT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _ensure_upload_dir(subfolder: str = "verifications") -> Path:
    base = Path(settings.STORAGE_PATH)
    target = base / subfolder
    target.mkdir(parents=True, exist_ok=True)
    return target


async def save_upload_image(
    file: UploadFile,
    *,
    user_id: int,
    occurrence_id: int,
    kind: str,  # single | before | after
) -> str:
    """
    Guarda una imagen subida y devuelve la ruta relativa (str)
    respecto a STORAGE_PATH, p.ej. 'verifications/u12_o45_single_xxx.jpg'
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido: {file.content_type}. Usa JPEG, PNG o WebP.",
        )

    content = await file.read()
    max_bytes = settings.MAX_PHOTO_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La imagen supera el límite de {settings.MAX_PHOTO_SIZE_MB} MB.",
        )
    if len(content) < 512:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo es demasiado pequeño o está vacío.",
        )

    ext = EXT_BY_CONTENT.get(file.content_type, ".jpg")
    filename = f"u{user_id}_o{occurrence_id}_{kind}_{uuid.uuid4().hex[:10]}{ext}"
    folder = _ensure_upload_dir("verifications")
    full_path = folder / filename
    full_path.write_bytes(content)

    # Ruta relativa para guardar en BD
    relative = f"verifications/{filename}"
    return relative


def absolute_path(relative: str) -> Path:
    """Convierte ruta relativa de BD a Path absoluto."""
    return Path(settings.STORAGE_PATH) / relative
