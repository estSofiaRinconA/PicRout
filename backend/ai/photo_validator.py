"""
Validador de fotos de evidencia – Paso 3.

Versión actual: validación básica de archivo (existencia, tamaño, tipo)
+ resultado con razón clara de por qué se acepta o se rechaza.

Diseñado para sustituirse por un modelo de visión real (o API externa)
sin cambiar la firma pública `validate_photo_evidence`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class PhotoValidationResult:
    accepted: bool
    confidence: float  # 0.0 – 1.0
    message: str  # Frase corta para el usuario (aprobado / rechazado)
    details: str | None = None  # Razón más detallada (por qué pasó o no)


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _check_file(path: str | Path, max_size_mb: int = 10) -> tuple[bool, str]:
    """Devuelve (ok, razón). La razón explica el fallo si ok=False."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False, "El archivo de foto no existe o no es accesible en el servidor."
    if p.suffix.lower() not in ALLOWED_EXTENSIONS:
        return (
            False,
            f"Formato no permitido ({p.suffix or 'sin extensión'}). "
            f"Usa: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
        )
    size_bytes = p.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    if size_mb > max_size_mb:
        return (
            False,
            f"La foto pesa {size_mb:.1f} MB y supera el límite de {max_size_mb} MB.",
        )
    if size_bytes < 1024:
        return (
            False,
            "El archivo es demasiado pequeño (< 1 KB) para ser una foto válida; "
            "puede estar vacío o corrupto.",
        )
    return True, "OK"


def validate_single_photo(
    photo_path: str,
    routine_name: str,
    routine_description: str | None = None,
    max_size_mb: int = 10,
) -> PhotoValidationResult:
    """
    Valida una foto única de evidencia.
    Siempre incluye una razón explícita de aceptación o rechazo.
    """
    ok, file_reason = _check_file(photo_path, max_size_mb)
    if not ok:
        return PhotoValidationResult(
            accepted=False,
            confidence=0.0,
            message="Foto rechazada: no cumple los requisitos técnicos.",
            details=file_reason,
        )

    # Validación heurística (sin visión LLM): archivo válido + contexto de rutina
    confidence = 0.78
    desc = (routine_description or "").strip()
    reason = (
        f"La foto se aceptó porque el archivo es válido (formato y tamaño correctos) "
        f"y se considera evidencia razonable de la rutina «{routine_name}»"
    )
    if desc:
        reason += f" ({desc[:120]})"
    reason += (
        f". Confianza estimada: {int(confidence * 100)}%. "
        "Sin modelo de visión activo se usa validación básica de archivo."
    )

    return PhotoValidationResult(
        accepted=True,
        confidence=confidence,
        message="Foto aprobada: evidencia aceptada.",
        details=reason,
    )


def validate_before_after(
    before_path: str,
    after_path: str,
    routine_name: str,
    routine_description: str | None = None,
    max_size_mb: int = 10,
) -> PhotoValidationResult:
    """
    Valida el par antes/después con razones claras.
    """
    ok_b, msg_b = _check_file(before_path, max_size_mb)
    if not ok_b:
        return PhotoValidationResult(
            accepted=False,
            confidence=0.0,
            message="Foto rechazada: la imagen ANTES no es válida.",
            details=f"Foto ANTES: {msg_b}",
        )

    ok_a, msg_a = _check_file(after_path, max_size_mb)
    if not ok_a:
        return PhotoValidationResult(
            accepted=False,
            confidence=0.0,
            message="Foto rechazada: la imagen DESPUÉS no es válida.",
            details=f"Foto DESPUÉS: {msg_a}",
        )

    if Path(before_path).resolve() == Path(after_path).resolve():
        return PhotoValidationResult(
            accepted=False,
            confidence=0.1,
            message="Fotos rechazadas: antes y después son el mismo archivo.",
            details=(
                "Se detectó que la foto ANTES y la foto DESPUÉS apuntan al mismo archivo. "
                "Para este método se necesitan dos evidencias distintas que muestren un cambio."
            ),
        )

    # Heurística: ambas válidas y distintas
    confidence = 0.75
    desc = (routine_description or "").strip()
    reason = (
        f"El par antes/después se aceptó porque ambas imágenes son válidas "
        f"(formato y tamaño correctos), son archivos distintos y se consideran "
        f"evidencia razonable de la rutina «{routine_name}»"
    )
    if desc:
        reason += f" ({desc[:120]})"
    reason += (
        f". Confianza estimada: {int(confidence * 100)}%. "
        "Sin modelo de visión activo se usa validación básica de archivo."
    )

    return PhotoValidationResult(
        accepted=True,
        confidence=confidence,
        message="Fotos aprobadas: par antes/después aceptado.",
        details=reason,
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
                accepted=False,
                confidence=0.0,
                message="Foto rechazada: no se envió ninguna imagen.",
                details="Falta el archivo de evidencia (campo photo) para el método foto única.",
            )
        return validate_single_photo(
            single_path, routine_name, routine_description, max_size_mb
        )
    if method == "before_after":
        if not before_path or not after_path:
            missing = []
            if not before_path:
                missing.append("ANTES (photo_before)")
            if not after_path:
                missing.append("DESPUÉS (photo_after)")
            return PhotoValidationResult(
                accepted=False,
                confidence=0.0,
                message="Fotos rechazadas: faltan imágenes del par antes/después.",
                details=f"Faltan: {', '.join(missing)}.",
            )
        return validate_before_after(
            before_path, after_path, routine_name, routine_description, max_size_mb
        )
    return PhotoValidationResult(
        accepted=False,
        confidence=0.0,
        message="Verificación rechazada: método no soportado.",
        details=f"El método fotográfico '{method}' no está soportado.",
    )
