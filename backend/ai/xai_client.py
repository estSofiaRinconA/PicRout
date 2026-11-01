"""
Compatibilidad: reexporta desde llm_client.
Preferir ai.llm_client en código nuevo.
"""
from ai.llm_client import (  # noqa: F401
    is_llm_configured as is_xai_configured,
    chat_completion,
    chat_completion_json,
    vision_completion,
    image_to_data_url,
    provider_label,
)
