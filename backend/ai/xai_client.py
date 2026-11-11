"""
Compatibilidad: reexporta desde llm_client.
Preferir ai.llm_client en código nuevo.
"""
from ai.llm_client import (  # noqa: F401
    is_llm_configured as is_xai_configured,
    chat_completion,
    chat_completion_json,
    provider_label,
)
