"""Конфигурация приложения.

Загружает настройки из переменных окружения (.env).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _env_or_none(name: str) -> str | None:
    value = os.getenv(name)
    return value or None


@dataclass
class Settings:
    service_name: str
    # Основной провайдер (OpenAI-совместимый API)
    api_key: str | None
    base_url: str | None
    primary_model: str
    classifier_model: str
    # Fallback-провайдер (OpenAI-совместимый API)
    fallback_api_key: str | None
    fallback_base_url: str | None
    fallback_model: str | None
    # Общие настройки
    request_timeout_seconds: float
    retry_attempts: int
    history_limit: int
    log_path: Path
    redis_host: str
    redis_port: int
    redis_ttl: int
    # Мультимодальные настройки
    tts_model: str
    tts_voice: str
    stt_model: str
    # Генерация изображений (OpenAI)
    imagegen_model: str

    @classmethod
    def from_env(cls) -> "Settings":
        base_dir = Path(__file__).resolve().parent.parent
        load_dotenv(base_dir / ".env", override=True)
        return cls(
            service_name=os.getenv("SUPPORT_SERVICE_NAME", "CloudBox"),
            api_key=_env_or_none("OPENAI_API_KEY"),
            base_url=_env_or_none("OPENAI_BASE_URL"),
            primary_model=os.getenv("SUPPORT_PRIMARY_MODEL", "gpt-4o-mini"),
            classifier_model=os.getenv("SUPPORT_CLASSIFIER_MODEL", "gpt-4o-mini"),
            fallback_api_key=_env_or_none("FALLBACK_API_KEY") or "ollama",
            fallback_base_url=_env_or_none("FALLBACK_BASE_URL") or "http://localhost:11434/v1",
            fallback_model=_env_or_none("FALLBACK_MODEL") or "gemma3:1b",
            request_timeout_seconds=float(os.getenv("SUPPORT_TIMEOUT_SECONDS", "30")),
            retry_attempts=int(os.getenv("SUPPORT_RETRY_ATTEMPTS", "3")),
            history_limit=int(os.getenv("SUPPORT_HISTORY_LIMIT", "10")),
            log_path=Path(os.getenv("SUPPORT_LOG_PATH", base_dir / "assistant.log")),
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_ttl=int(os.getenv("REDIS_TTL", "3600")),
            tts_model=os.getenv("SUPPORT_TTS_MODEL", "tts-1"),
            tts_voice=os.getenv("SUPPORT_TTS_VOICE", "nova"),
            stt_model=os.getenv("SUPPORT_STT_MODEL", "whisper-1"),
            imagegen_model=os.getenv("IMAGEGEN_MODEL", "gpt-image-1"),
        )
