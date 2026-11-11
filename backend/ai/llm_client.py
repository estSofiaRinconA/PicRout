"""
Cliente LLM unificado para PicRout – prioriza opciones GRATIS.

Orden de prioridad:
  1. Groq   (GROQ_API_KEY)  → free tier, OpenAI-compatible, muy rápido
  2. Gemini (GEMINI_API_KEY) → free tier de Google AI Studio
  3. xAI    (XAI_API_KEY)   → opcional / de pago
  4. (sin key) → las capas superiores usan heurísticas locales

Solo texto por chat/completions estilo OpenAI (Groq y xAI).
Gemini usa su endpoint generateContent.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

import httpx

from App.config import get_settings

logger = logging.getLogger("picrout.llm")

DEFAULT_TIMEOUT = 60.0

Provider = Literal["groq", "gemini", "xai", "none"]


def get_active_provider() -> Provider:
    """Devuelve el proveedor configurado con mayor prioridad (gratis primero)."""
    s = get_settings()
    if not getattr(s, "AI_USE_LLM", True):
        return "none"
    if (s.GROQ_API_KEY or "").strip():
        return "groq"
    if (s.GEMINI_API_KEY or "").strip():
        return "gemini"
    if (s.XAI_API_KEY or "").strip():
        return "xai"
    return "none"


def is_llm_configured() -> bool:
    return get_active_provider() != "none"


def provider_label() -> str:
    p = get_active_provider()
    return {
        "groq": "Groq (gratis)",
        "gemini": "Gemini (gratis)",
        "xai": "Grok/xAI",
        "none": "heurísticas locales",
    }.get(p, p)


# ---------- OpenAI-compatible (Groq / xAI) ----------

def _openai_compat_chat(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float,
    max_tokens: int,
    response_format: dict | None,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    # Groq soporta json_object en varios modelos; si falla, reintentamos sin él
    if response_format:
        payload["response_format"] = response_format

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{base_url.rstrip('/')}/chat/completions"

    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400 and response_format:
            # reintento sin response_format (algunos modelos free no lo soportan)
            payload.pop("response_format", None)
            resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Respuesta inesperada del LLM: {data!r}") from e


# ---------- Gemini free ----------

def _gemini_chat(
    *,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float,
    max_tokens: int,
) -> str:
    """
    Traduce messages OpenAI-like a generateContent de Gemini.
    """
    system_parts: list[str] = []
    contents: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            # multimodal no implementado aquí para Gemini en esta versión texto
            text = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        else:
            text = str(content)
        if role == "system":
            system_parts.append(text)
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": text}]})
        else:
            contents.append({"role": "user", "parts": [{"text": text}]})

    body: dict[str, Any] = {
        "contents": contents or [{"role": "user", "parts": [{"text": "Hola"}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_parts:
        body["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.post(
            url,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Respuesta inesperada de Gemini: {data!r}") from e


# ---------- API pública ----------

def chat_completion(
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    response_format: dict | None = None,
) -> str:
    s = get_settings()
    provider = get_active_provider()

    if provider == "groq":
        return _openai_compat_chat(
            base_url="https://api.groq.com/openai/v1",
            api_key=s.GROQ_API_KEY.strip(),
            model=(s.GROQ_MODEL or "llama-3.1-8b-instant").strip(),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
    if provider == "xai":
        return _openai_compat_chat(
            base_url="https://api.x.ai/v1",
            api_key=s.XAI_API_KEY.strip(),
            model=(s.XAI_MODEL or "grok-4").strip(),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
    if provider == "gemini":
        return _gemini_chat(
            api_key=s.GEMINI_API_KEY.strip(),
            model=(s.GEMINI_MODEL or "gemini-2.5-flash").strip(),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    raise RuntimeError("Ningún proveedor LLM configurado")


def chat_completion_json(
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> dict | list:
    text = chat_completion(
        messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    text = text.strip()
    if text.startswith("```"):
        lines = [ln for ln in text.split("\n") if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    # a veces el modelo añade texto antes/después del JSON
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)
