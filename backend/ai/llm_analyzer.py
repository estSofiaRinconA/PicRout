"""
Análisis de rutinas con LLM + fallback heurístico.

API pública: analyze_routine_smart(name, description) -> AnalysisResult
Método de verificación: siempre quiz (fotos eliminadas).
"""

from __future__ import annotations

import logging

from ai.analyzer import AnalysisResult, analyze_routine as heuristic_analyze
from ai.llm_client import is_llm_configured as is_xai_configured, chat_completion_json, provider_label

logger = logging.getLogger("picrout.llm_analyzer")

SYSTEM_PROMPT = """Eres el motor de IA de PicRout, una app de hábitos.
Analizas el nombre y la descripción de una rutina y decides SOLO dificultad y puntos.
El método de verificación es siempre "quiz" (no uses fotos).

1. verification_method: siempre "quiz"
2. base_points: entero entre 5 y 30 según dificultad
   - fácil (levantarse, beber agua, hacer la cama): 5-8
   - media (ejercicio corto, limpieza, lectura breve): 10-15
   - difícil (estudio intenso, proyecto, 2+ horas): 18-30
3. difficulty: "facil" | "media" | "dificil"
4. reason: una frase corta en español explicando la dificultad
5. confidence: float 0.0-1.0

Responde SOLO con un JSON válido con estas claves:
verification_method, base_points, difficulty, reason, confidence
"""


def _parse_llm_result(data: dict) -> AnalysisResult:
    points = int(data.get("base_points", 10))
    points = max(5, min(30, points))
    difficulty = str(data.get("difficulty", "media")).strip().lower()
    if difficulty not in ("facil", "media", "dificil"):
        difficulty = "media"
    reason = str(data.get("reason", "Análisis por IA.")).strip()
    conf = float(data.get("confidence", 0.8))
    conf = max(0.0, min(1.0, conf))
    return AnalysisResult(
        verification_method="quiz",
        base_points=points,
        difficulty=difficulty,
        reason=reason,
        confidence=round(conf, 2),
    )


def analyze_routine_smart(name: str, description: str | None = None) -> AnalysisResult:
    """
    Usa LLM si hay API key configurada; si no, o si falla, usa heurísticas.
    Siempre devuelve verification_method="quiz".
    """
    if not name or not name.strip():
        raise ValueError("El nombre de la rutina es obligatorio para el análisis.")

    if not is_xai_configured():
        return heuristic_analyze(name, description)

    user_msg = (
        f"Nombre: {name.strip()}\n"
        f"Descripción: {(description or '').strip() or '(sin descripción)'}"
    )
    try:
        data = chat_completion_json(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        if not isinstance(data, dict):
            raise ValueError("JSON no es objeto")
        result = _parse_llm_result(data)
        result.reason = f"[{provider_label()}] {result.reason}"
        return result
    except Exception as e:
        logger.warning("LLM analyze falló (%s); usando heurística", e)
        return heuristic_analyze(name, description)
