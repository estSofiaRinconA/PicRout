"""
Motor de análisis de rutinas – Paso 3.

A partir del nombre y la descripción decide:
- método de verificación: single_photo | before_after | quiz
- puntaje base por dificultad (5–30)

Implementación actual: heurísticas en español + reglas de dominio.
Diseñado para poder sustituir/complementar con un LLM real sin cambiar la API pública.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

VerificationMethod = Literal["single_photo", "before_after", "quiz"]


@dataclass
class AnalysisResult:
    verification_method: VerificationMethod
    base_points: int
    difficulty: str  # facil | media | dificil
    reason: str
    confidence: float  # 0.0 – 1.0


# ---------- Vocabularios (español) ----------

BEFORE_AFTER_KEYWORDS = [
    "limpiar", "limpieza", "ordenar", "organización", "organizar", "organizar",
    "arreglar", "decorar", "pintar", "montar", "armar", "construir", "ensamblar",
    "cocinar", "preparar comida", "preparar la comida", "lavar", "fregar",
    "barrer", "trapear", "aspirar", "doblar", "guardar ropa", "hacer la cama",
    "cambiar sábanas", "jardín", "plantar", "regar", "podar", "manualidad",
    "diy", "reparar", "arreglar", "renovar", "transformar", "antes y después",
    "antes/después", "estado inicial", "estado final",
]

SINGLE_PHOTO_KEYWORDS = [
    "llegar", "llegada", "ubicarme", "ubicación", "check-in", "check in",
    "gym", "gimnasio", "entrenar", "ejercicio", "correr", "caminar",
    "vestir", "vestirme", "outfit", "ropa", "uniforme",
    "ticket", "tiquete", "recibo", "factura", "compra", "pagar",
    "medicamento", "pastilla", "tomar medicina", "medicina",
    "beber agua", "tomar agua", "hidratación",
    "despertar", "levantarme", "cama", "amanecer",
    "ducha", "ducharme", "baño",
    "selfie", "foto", "evidencia visual",
]

QUIZ_KEYWORDS = [
    "leer", "lectura", "libro", "capítulo", "páginas",
    "estudiar", "estudio", "repasar", "aprender", "memorizar",
    "tema", "materia", "asignatura", "curso", "clase",
    "meditar", "meditación", "mindfulness", "respiración",
    "escribir", "diario", "journaling", "reflexionar",
    "practicar idioma", "vocabulario", "gramática",
    "resolver", "ejercicios de", "problemas de", "matemáticas",
    "programar", "código", "coding", "algoritmo",
    "escuchar podcast", "podcast", "audiolibro",
    "pensar", "planificar", "plan", "objetivos",
]

# Actividades típicamente fáciles / medias / difíciles
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


def _choose_method(name: str, description: str | None) -> tuple[VerificationMethod, str, float]:
    combined = _normalize(f"{name} {description or ''}")

    score_ba = _score_keywords(combined, BEFORE_AFTER_KEYWORDS)
    score_sp = _score_keywords(combined, SINGLE_PHOTO_KEYWORDS)
    score_qz = _score_keywords(combined, QUIZ_KEYWORDS)

    # Preferencias explícitas del usuario
    if "antes y despues" in combined or "antes despues" in combined or "antes/despues" in combined:
        return "before_after", "La descripción menciona explícitamente antes/después.", 0.95
    if "quiz" in combined or "pregunta" in combined or "cuestionario" in combined:
        return "quiz", "La descripción pide verificación por preguntas.", 0.9

    scores = {
        "before_after": score_ba,
        "single_photo": score_sp,
        "quiz": score_qz,
    }
    best = max(scores, key=scores.get)
    best_score = scores[best]

    if best_score == 0:
        # Por defecto: si suena cognitivo → quiz, si no → foto única
        if any(w in combined for w in ("estudi", "leer", "aprend", "pensar", "memori")):
            return "quiz", "Sin coincidencias fuertes; actividad cognitiva → quiz.", 0.55
        return "single_photo", "Sin coincidencias fuertes; se usa foto única por defecto.", 0.5

    reasons = {
        "before_after": "Palabras clave de cambio de estado / limpieza / organización.",
        "single_photo": "Palabras clave de evidencia visual puntual (lugar, outfit, ticket, etc.).",
        "quiz": "Palabras clave de actividad cognitiva o de estudio.",
    }
    conf = min(0.55 + 0.12 * best_score, 0.92)
    return best, reasons[best], conf  # type: ignore[return-value]


def _choose_points(name: str, description: str | None, method: VerificationMethod) -> tuple[int, str]:
    combined = _normalize(f"{name} {description or ''}")

    easy = _score_keywords(combined, EASY_HINTS)
    medium = _score_keywords(combined, MEDIUM_HINTS)
    hard = _score_keywords(combined, HARD_HINTS)

    # Duración implícita
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
        # Defaults por método
        defaults = {"single_photo": 8, "before_after": 12, "quiz": 15}
        points = defaults[method]
        difficulty = "media" if points >= 12 else "facil"

    # Ajustes finos
    if method == "quiz" and points < 10:
        points = 12
        difficulty = "media"
    if method == "before_after" and points < 10:
        points = 12
        difficulty = "media"

    points = max(5, min(30, points))
    return points, difficulty


def analyze_routine(name: str, description: str | None = None) -> AnalysisResult:
    """
    Analiza nombre + descripción y devuelve método de verificación y puntos.
    """
    if not name or not name.strip():
        raise ValueError("El nombre de la rutina es obligatorio para el análisis.")

    method, reason, confidence = _choose_method(name, description)
    points, difficulty = _choose_points(name, description, method)

    full_reason = f"{reason} Dificultad estimada: {difficulty}."
    return AnalysisResult(
        verification_method=method,
        base_points=points,
        difficulty=difficulty,
        reason=full_reason,
        confidence=round(confidence, 2),
    )
