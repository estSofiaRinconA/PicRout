"""
Motor de análisis de rutinas – Paso 3.

A partir del nombre y la descripción estima:
- puntaje base por dificultad (5–30)
- método de verificación: siempre "quiz"

(La verificación por fotos fue eliminada del proyecto.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

VerificationMethod = Literal["quiz"]


@dataclass
class AnalysisResult:
    verification_method: VerificationMethod
    base_points: int
    difficulty: str  # facil | media | dificil
    reason: str
    confidence: float  # 0.0 – 1.0


EASY_HINTS = [
    "levantarse", "despertar", "beber agua", "tomar agua", "ducha", "ducharme",
    "hacer la cama", "tomar medicina", "pastilla", "estirar", "caminar 10",
]
MEDIUM_HINTS = [
    "ejercicio", "entrenar", "gym", "gimnasio", "correr", "limpiar", "ordenar",
    "leer", "meditar", "cocinar", "estudiar 30", "estudiar media",
]
HARD_HINTS = [
    "estudiar", "aprender", "proyecto", "programar", "escribir ensayo",
    "examen", "tema difícil", "capítulo completo", "2 horas", "tres horas",
    "maratón", "entrenar fuerte", "rutina completa",
]


def _normalize(text: str) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"[áàäâ]", "a", t)
    t = re.sub(r"[éèëê]", "e", t)
    t = re.sub(r"[íìïî]", "i", t)
    t = re.sub(r"[óòöô]", "o", t)
    t = re.sub(r"[úùüû]", "u", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _score_keywords(text: str, keywords: list[str]) -> int:
    return sum(1 for kw in keywords if kw in text)


def _choose_points(name: str, description: str | None) -> tuple[int, str]:
    combined = _normalize(f"{name} {description or ''}")

    easy = _score_keywords(combined, EASY_HINTS)
    medium = _score_keywords(combined, MEDIUM_HINTS)
    hard = _score_keywords(combined, HARD_HINTS)

    if re.search(r"\b([2-9]|1[0-9])\s*h(oras?)?\b", combined) or "2 horas" in combined:
        hard += 2
    if re.search(r"\b(30|45|60)\s*min", combined) or "media hora" in combined:
        medium += 1

    if hard > medium and hard > easy:
        points, difficulty = 22, "dificil"
    elif medium >= easy and medium > 0:
        points, difficulty = 12, "media"
    elif easy > 0:
        points, difficulty = 6, "facil"
    else:
        points, difficulty = 12, "media"

    points = max(5, min(30, points))
    return points, difficulty


def analyze_routine(name: str, description: str | None = None) -> AnalysisResult:
    """
    Analiza nombre + descripción y devuelve puntos / dificultad.
    Método de verificación fijo: quiz.
    """
    if not name or not name.strip():
        raise ValueError("El nombre de la rutina es obligatorio para el análisis.")

    points, difficulty = _choose_points(name, description)
    reason = (
        f"Verificación por quiz. Dificultad estimada: {difficulty} "
        f"({points} puntos base)."
    )
    return AnalysisResult(
        verification_method="quiz",
        base_points=points,
        difficulty=difficulty,
        reason=reason,
        confidence=0.75,
    )
