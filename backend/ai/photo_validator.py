"""
Validador de fotos de evidencia – Paso 3.

Versión actual: validación básica de archivo (existencia, tamaño, tipo)
+ resultado "aceptado" con confianza media.

Diseñado para sustituirse por un modelo de visión real (o API externa)
sin cambiar la firma pública `validate_photo_evidence`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class PhotoValidationResult:
    accepted: bool
    confidence: float  # 0.0 – 1.0
    message: str
    details: str | None = None


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
# Tipos MIME aproximados por extensión
MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _check_file(path: str | Path, max_size_mb: int = 10) -> tuple[bool, str]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False, "El archivo de foto no existe o no es accesible."
    if p.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False, f"Formato no permitido. Usa: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    size_mb = p.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"La foto supera el límite de {max_size_mb} MB."
    if p.stat().st_size < 1024:  # < 1 KB probablemente inválida
        return False, "El archivo es demasiado pequeño para ser una foto válida."
    return True, "OK"


def validate_single_photo(
    photo_path: str,
    routine_name: str,
    routine_description: str | None = None,
    max_size_mb: int = 10,
) -> PhotoValidationResult:
    """
    Valida una foto única de evidencia.
    Por ahora: checks de archivo + aceptación con confianza base.
    """
    ok, msg = _check_file(photo_path, max_size_mb)
    if not ok:
        return PhotoValidationResult(accepted=False, confidence=0.0, message=msg)

    # Placeholder de visión: en producción aquí iría el modelo
    confidence = 0.78
    return PhotoValidationResult(
        accepted=True,
        confidence=confidence,
        message="Foto recibida y validada (verificación básica). Evidencia aceptada.",
        details=f"Rutina: {routine_name}. Validación de archivo OK.",
    )


def validate_before_after(
    before_path: str,
    after_path: str,
    routine_name: str,
    routine_description: str | None = None,
    max_size_mb: int = 10,
) -> PhotoValidationResult:
    """
    Valida el par antes/después.
    """
    ok_b, msg_b = _check_file(before_path, max_size_mb)
    if not ok_b:
        return PhotoValidationResult(accepted=False, confidence=0.0, message=f"Foto ANTES: {msg_b}")

    ok_a, msg_a = _check_file(after_path, max_size_mb)
    if not ok_a:
        return PhotoValidationResult(accepted=False, confidence=0.0, message=f"Foto DESPUÉS: {msg_a}")

    if Path(before_path).resolve() == Path(after_path).resolve():
        return PhotoValidationResult(
            accepted=False,
            confidence=0.1,
            message="Las fotos antes y después parecen ser el mismo archivo.",
        )

    confidence = 0.75
    return PhotoValidationResult(
        accepted=True,
        confidence=confidence,
        message="Par antes/después recibido y validado (verificación básica). Evidencia aceptada.",
        details=f"Rutina: {routine_name}. Ambas fotos OK.",
    )


def validate_photo_evidence(
    method: Literal["single_photo", "before_after"],
    *,
    single_path: str | None = None,
    before_path: str | None = None,
    after_path: str | None = None,
    routine_name: str = "",
    routine_description: str | None = None,
    max_size_mb: int = 10,
) -> PhotoValidationResult:
    """API pública estable para validar evidencias fotográficas."""
    if method == "single_photo":
        if not single_path:
            return PhotoValidationResult(
                accepted=False, confidence=0.0, message="Falta la foto de evidencia."
            )
        return validate_single_photo(
            single_path, routine_name, routine_description, max_size_mb
        )
    if method == "before_after":
        if not before_path or not after_path:
            return PhotoValidationResult(
                accepted=False,
                confidence=0.0,
                message="Se requieren ambas fotos: antes y después.",
            )
        return validate_before_after(
            before_path, after_path, routine_name, routine_description, max_size_mb
        )
    return PhotoValidationResult(
        accepted=False, confidence=0.0, message=f"Método fotográfico no soportado: {method}"
    )
