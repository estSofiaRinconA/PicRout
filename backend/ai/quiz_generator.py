"""
Generador de quizzes para verificación de rutinas – Paso 3.

Implementación basada en plantillas + heurísticas en español.
Diseñado para poder sustituirse por un LLM real sin cambiar la firma pública.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, asdict


@dataclass
class QuizQuestion:
    id: int
    question: str
    options: list[str]
    correct_index: int  # 0-based


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


# Plantillas genéricas por dominio
TEMPLATES = {
    "lectura": [
        {
            "q": "¿Cuál es un buen hábito al terminar de leer?",
            "options": [
                "Anotar una idea o frase que te haya impactado",
                "Cerrar el libro y olvidarlo",
                "Saltar al siguiente libro sin reflexionar",
                "Dejar el libro abierto toda la noche",
            ],
            "correct": 0,
        },
        {
            "q": "¿Qué ayuda a recordar mejor lo leído?",
            "options": [
                "Leer solo títulos",
                "Explicarlo con tus propias palabras",
                "Subrayar todo el texto",
                "Leer muy rápido sin pausas",
            ],
            "correct": 1,
        },
        {
            "q": "Si la rutina es de lectura, ¿qué indica que la completaste con calidad?",
            "options": [
                "Solo abriste el libro",
                "Dedicaste el tiempo planeado y prestaste atención",
                "Leíste mientras veías series",
                "Solo miraste las páginas",
            ],
            "correct": 1,
        },
    ],
    "estudio": [
        {
            "q": "¿Qué técnica suele mejorar la retención al estudiar?",
            "options": [
                "Estudiar 8 horas seguidas sin descanso",
                "Repaso activo y explicarte el tema en voz alta",
                "Solo subrayar de colores",
                "Memorizar sin entender",
            ],
            "correct": 1,
        },
        {
            "q": "¿Cuándo es mejor hacer una pausa corta?",
            "options": [
                "Nunca, hay que estudiar sin parar",
                "Cada 25–50 minutos de concentración",
                "Solo al final del día",
                "Cada 2 minutos",
            ],
            "correct": 1,
        },
        {
            "q": "Si estudias un tema difícil, ¿qué es más efectivo?",
            "options": [
                "Repetir en bucle sin entender",
                "Dividir en partes pequeñas y practicar",
                "Cambiar de tema cada minuto",
                "Copiar sin leer",
            ],
            "correct": 1,
        },
    ],
    "meditacion": [
        {
            "q": "¿Qué suele indicar una sesión de meditación útil?",
            "options": [
                "Pensar en la lista de tareas todo el tiempo",
                "Volver suavemente la atención a la respiración cuando te distraes",
                "Forzarte a no pensar en nada",
                "Meditar con la TV encendida",
            ],
            "correct": 1,
        },
        {
            "q": "¿Qué postura es generalmente recomendable?",
            "options": [
                "Totalmente rígida e incómoda",
                "Cómoda, con la espalda razonablemente erguida",
                "Acostado y a punto de dormirte siempre",
                "De pie y caminando rápido",
            ],
            "correct": 1,
        },
    ],
    "idioma": [
        {
            "q": "¿Qué práctica ayuda más a aprender un idioma?",
            "options": [
                "Solo traducir palabra por palabra",
                "Usar el idioma activamente (hablar, escribir, escuchar)",
                "Memorizar diccionarios enteros",
                "Evitar cometer errores a toda costa",
            ],
            "correct": 1,
        },
        {
            "q": "Si practicaste vocabulario, ¿qué demuestra progreso real?",
            "options": [
                "Reconocer las palabras en contexto",
                "Solo copiarlas en un cuaderno",
                "Olvidarlas al día siguiente sin repaso",
                "Evitar usarlas",
            ],
            "correct": 0,
        },
    ],
    "generico": [
        {
            "q": "¿Qué indica que completaste esta rutina de forma consciente?",
            "options": [
                "La marcaste sin hacerla",
                "Dedicaste atención y el tiempo planeado a la actividad",
                "La dejaste a medias sin motivo",
                "La pospusiste indefinidamente",
            ],
            "correct": 1,
        },
        {
            "q": "¿Por qué es útil verificar con preguntas una actividad mental?",
            "options": [
                "Para perder tiempo",
                "Porque no siempre hay evidencia visual clara",
                "Para complicar la app",
                "Porque las fotos no existen",
            ],
            "correct": 1,
        },
        {
            "q": "Si la actividad era de reflexión o aprendizaje, ¿qué es un buen indicador?",
            "options": [
                "No recordar nada al terminar",
                "Poder resumir lo principal en pocas frases",
                "Haberla hecho distraído",
                "Haberla saltado",
            ],
            "correct": 1,
        },
    ],
}


def _detect_domain(name: str, description: str | None) -> str:
    text = _normalize(f"{name} {description or ''}")
    if any(w in text for w in ("leer", "lectura", "libro", "capitulo", "pagina")):
        return "lectura"
    if any(w in text for w in ("estudi", "repasar", "aprender", "memoriz", "examen", "tema", "materia")):
        return "estudio"
    if any(w in text for w in ("medit", "mindfulness", "respiracion", "relaj")):
        return "meditacion"
    if any(w in text for w in ("idioma", "ingles", "vocabulario", "gramatica", "hablar")):
        return "idioma"
    return "generico"


def generate_quiz(
    name: str,
    description: str | None = None,
    num_questions: int = 3,
) -> list[dict]:
    """
    Genera un quiz de `num_questions` preguntas (máx. disponibles en el dominio).
    Devuelve lista de dicts listos para guardar en JSON.
    """
    domain = _detect_domain(name, description)
    pool = list(TEMPLATES.get(domain, TEMPLATES["generico"]))
    # Mezclar con genéricas si hace falta
    if len(pool) < num_questions:
        pool = pool + list(TEMPLATES["generico"])

    random.shuffle(pool)
    selected = pool[:num_questions]

    questions: list[dict] = []
    for i, item in enumerate(selected):
        options = list(item["options"])
        correct = item["correct"]
        # Mezclar opciones manteniendo el índice correcto
        paired = list(enumerate(options))
        random.shuffle(paired)
        new_options = [opt for _, opt in paired]
        new_correct = next(idx for idx, (orig_i, _) in enumerate(paired) if orig_i == correct)

        q = QuizQuestion(
            id=i,
            question=item["q"],
            options=new_options,
            correct_index=new_correct,
        )
        questions.append(asdict(q))

    return questions


def grade_quiz(questions: list[dict], answers: dict) -> tuple[float, int, int]:
    """
    answers: {"0": 1, "1": 0, ...}  (str keys o int keys)
    Devuelve (score 0-1, correctas, total)
    """
    if not questions:
        return 0.0, 0, 0

    correct = 0
    total = len(questions)
    for q in questions:
        qid = str(q["id"])
        user_ans = answers.get(qid, answers.get(q["id"]))
        if user_ans is None:
            continue
        try:
            if int(user_ans) == int(q["correct_index"]):
                correct += 1
        except (TypeError, ValueError):
            continue

    score = correct / total if total else 0.0
    return round(score, 2), correct, total
