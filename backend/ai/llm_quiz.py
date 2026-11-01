"""
Generación de quizzes con Grok + fallback a plantillas.
"""

from __future__ import annotations

import logging
from typing import Any

from ai.quiz_generator import generate_quiz as heuristic_quiz, grade_quiz
from ai.llm_client import is_llm_configured as is_xai_configured, chat_completion_json

logger = logging.getLogger("picrout.llm_quiz")

SYSTEM_PROMPT = """Eres el generador de quizzes de PicRout.
Creas preguntas de verificación para confirmar que el usuario REALMENTE realizó
una actividad mental (leer, estudiar, meditar, etc.).

Reglas:
- Genera exactamente el número de preguntas pedido.
- Cada pregunta tiene 4 opciones (índices 0-3).
- Solo UNA opción es correcta.
- Preguntas en español, claras y relacionadas con la rutina.
- No pidas datos imposibles de saber; enfócate en comprensión, hábitos de estudio
  o señales de que la actividad se hizo con atención.
- correct_index es 0-based.

Responde SOLO con JSON:
{
  "questions": [
    {
      "id": 0,
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "correct_index": 1
    }
  ]
}
"""


def generate_quiz_smart(
    name: str,
    description: str | None = None,
    num_questions: int = 3,
) -> list[dict[str, Any]]:
    if not is_xai_configured():
        return heuristic_quiz(name, description, num_questions)

    user_msg = (
        f"Rutina: {name}\n"
        f"Descripción: {description or '(sin descripción)'}\n"
        f"Número de preguntas: {num_questions}"
    )
    try:
        data = chat_completion_json(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.5,
            max_tokens=900,
        )
        questions = data.get("questions") if isinstance(data, dict) else None
        if not isinstance(questions, list) or not questions:
            raise ValueError("Sin questions en respuesta")

        cleaned: list[dict[str, Any]] = []
        for i, q in enumerate(questions[:num_questions]):
            options = list(q.get("options") or [])
            if len(options) < 2:
                raise ValueError("Opciones insuficientes")
            # rellenar hasta 4 si hace falta
            while len(options) < 4:
                options.append(f"Opción {len(options) + 1}")
            options = options[:4]
            correct = int(q.get("correct_index", 0))
            correct = max(0, min(3, correct))
            cleaned.append(
                {
                    "id": i,
                    "question": str(q.get("question", f"Pregunta {i + 1}")).strip(),
                    "options": [str(o) for o in options],
                    "correct_index": correct,
                }
            )
        if len(cleaned) < num_questions:
            # completar con heurística
            extra = heuristic_quiz(name, description, num_questions - len(cleaned))
            for j, eq in enumerate(extra):
                eq["id"] = len(cleaned) + j
                cleaned.append(eq)
        return cleaned
    except Exception as e:
        logger.warning("Grok quiz falló (%s); usando plantillas", e)
        return heuristic_quiz(name, description, num_questions)


# Re-export grade para no romper imports
__all__ = ["generate_quiz_smart", "grade_quiz"]
