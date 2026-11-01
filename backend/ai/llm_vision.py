"""
Validación de evidencias fotográficas con visión de Grok + fallback básico.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ai.photo_validator import PhotoValidationResult, validate_photo_evidence as heuristic_validate
from ai.llm_client import is_llm_configured as is_xai_configured, vision_completion

logger = logging.getLogger("picrout.llm_vision")

SYSTEM_PROMPT = """Eres el verificador visual de PicRout, una app de hábitos.
Tu trabajo: decidir si la(s) foto(s) son evidencia razonable de que el usuario
completó la rutina indicada.

Sé práctico, no excesivamente estricto:
- Acepta evidencias plausibles aunque no sean perfectas.
- Rechaza fotos irrelevantes, vacías, memes obvios o que no tengan relación.
- Para before/after: debe haber un cambio visible o al menos dos momentos distintos.

Responde SOLO con JSON:
{
  "accepted": true/false,
  "confidence": 0.0-1.0,
  "message": "frase corta en español para el usuario",
  "details": "análisis breve interno"
}
"""


def _parse_vision(text: str) -> PhotoValidationResult:
    raw = text.strip()
    if raw.startswith("```"):
        lines = [ln for ln in raw.split("\n") if not ln.strip().startswith("```")]
        raw = "\n".join(lines).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Si el modelo no devolvió JSON, interpretar texto libre de forma conservadora
        lower = text.lower()
        accepted = any(w in lower for w in ("acept", "válid", "valid", "sí", "si,", "cumple"))
        return PhotoValidationResult(
            accepted=accepted,
            confidence=0.6 if accepted else 0.3,
            message=text[:200],
            details="Respuesta no-JSON de Grok",
        )
    accepted = bool(data.get("accepted", False))
    conf = float(data.get("confidence", 0.5))
    conf = max(0.0, min(1.0, conf))
    return PhotoValidationResult(
        accepted=accepted,
        confidence=round(conf, 2),
        message=str(data.get("message", "")).strip() or ("Evidencia aceptada." if accepted else "Evidencia no aceptada."),
        details=str(data.get("details", "")).strip() or None,
    )


def validate_photo_smart(
    method: str,
    *,
    single_path: str | None = None,
    before_path: str | None = None,
    after_path: str | None = None,
    routine_name: str = "",
    routine_description: str | None = None,
    max_size_mb: int = 10,
) -> PhotoValidationResult:
    """
    Primero checks de archivo (heurística). Si pasan y hay XAI_API_KEY,
    pregunta a Grok con visión. Si no hay key o falla, usa el resultado heurístico.
    """
    # Validación de archivo siempre
    basic = heuristic_validate(
        method,  # type: ignore[arg-type]
        single_path=single_path,
        before_path=before_path,
        after_path=after_path,
        routine_name=routine_name,
        routine_description=routine_description,
        max_size_mb=max_size_mb,
    )
    if not basic.accepted:
        return basic

    if not is_xai_configured():
        return basic

    paths: list[str] = []
    if method == "single_photo" and single_path:
        paths = [single_path]
        prompt = (
            f"Rutina: {routine_name}\n"
            f"Descripción: {routine_description or '(ninguna)'}\n"
            f"Método: foto única.\n"
            "¿Esta foto es evidencia razonable de que se realizó la actividad?"
        )
    elif method == "before_after" and before_path and after_path:
        paths = [before_path, after_path]
        prompt = (
            f"Rutina: {routine_name}\n"
            f"Descripción: {routine_description or '(ninguna)'}\n"
            f"Método: antes y después.\n"
            "La PRIMERA imagen es ANTES y la SEGUNDA es DESPUÉS.\n"
            "¿El par demuestra un cambio o progreso coherente con la rutina?"
        )
    else:
        return basic

    # Comprobar que los archivos existen
    for p in paths:
        if not Path(p).is_file():
            return PhotoValidationResult(
                accepted=False, confidence=0.0, message=f"Archivo no encontrado: {p}"
            )

    try:
        text = vision_completion(
            prompt,
            paths,
            system=SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=500,
        )
        result = _parse_vision(text)
        if result.details:
            result.details = f"[Grok] {result.details}"
        else:
            result.details = "[Grok] visión"
        return result
    except Exception as e:
        logger.warning("Grok vision falló (%s); usando validación básica", e)
        basic.details = f"Fallback heurístico tras error Grok: {e}"
        return basic
