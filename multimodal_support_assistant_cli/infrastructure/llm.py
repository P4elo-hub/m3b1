"""Клиент LLM с retry (tenacity) и fallback.

Все провайдеры работают через OpenAI-совместимый API.
Цепочка: primary → fallback → эскалация на оператора.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from loguru import logger
from openai import OpenAI, RateLimitError, APIStatusError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from config import Settings
from models import Category, ClassificationResult, LLMResult
from core.classification import heuristic_classify

# Ответ-заглушка, когда ни один провайдер не дал полезный ответ
FALLBACK_ANSWER = "К сожалению, сейчас не удалось получить ответ от LLM-провайдера."


def _build_client(api_key: str | None, base_url: str | None) -> OpenAI | None:
    """Создаёт OpenAI-совместимый клиент, если есть ключ."""
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=base_url)


class RobustLLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.primary = _build_client(settings.api_key, settings.base_url)
        self.fallback = _build_client(settings.fallback_api_key, settings.fallback_base_url)
        if self.primary is None:
            logger.warning("Primary API недоступен: не задан OPENAI_API_KEY")
        if self.fallback is None:
            logger.warning("Fallback API недоступен: не задан FALLBACK_API_KEY")

    # ── Цепочка провайдеров ───────────────────────────────────────────

    def _provider_chain(self) -> Iterator[tuple[OpenAI, str, bool]]:
        """Отдаёт (client, model, used_fallback) для каждого доступного провайдера."""
        if self.primary is not None:
            yield self.primary, self.settings.primary_model, False
        if self.fallback is not None and self.settings.fallback_model:
            yield self.fallback, self.settings.fallback_model, True

    # ── Публичные методы ──────────────────────────────────────────────

    def classify(self, messages: list[dict[str, str]]) -> ClassificationResult:
        """Классифицирует запрос: primary → fallback → локальная эвристика."""
        for client, _, used_fallback in self._provider_chain():
            model = self.settings.fallback_model if used_fallback else self.settings.classifier_model
            provider = "fallback" if used_fallback else "primary"
            try:
                raw, _ = self._call(client, model, messages, temperature=0, max_tokens=350)
                return self._parse_classifier_result(raw, provider)
            except Exception as e:
                logger.warning(
                    "Не удалось выполнить классификацию через {} API, model={}: {}",
                    provider, model, e,
                )
                continue

        logger.warning("Классификация через API недоступна, используется локальная эвристика")
        category = heuristic_classify(messages[-1]["content"])
        return ClassificationResult(
            category=category,
            priority="unknown",
            summary="Классификация выполнена локальной эвристикой",
            source="heuristic",
        )

    def _parse_classifier_result(self, raw: str, source: str) -> ClassificationResult:
        """Достаёт полный JSON-результат классификатора или поддерживает старый plain-text формат."""
        text = raw.strip()
        if text.startswith("```"):
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        if text.startswith("{"):
            payload = json.loads(text)
            category = str(payload["category"]).strip().lower()
            return ClassificationResult(
                category=Category(category),
                priority=str(payload.get("priority", "unknown")),
                summary=str(payload.get("summary", "")),
                entities=payload.get("entities") or {
                    "services": [],
                    "error_codes": [],
                    "environment": "unknown",
                },
                requires_immediate_escalation=False,
                confidence=float(payload.get("confidence", 0.0)),
                source=source,
            )
        else:
            category = text.lower()

        return ClassificationResult(category=Category(category), source=source)

    def answer(self, messages: list[dict[str, Any]]) -> LLMResult:
        """Получает ответ: primary → fallback → эскалация."""
        for client, model, used_fallback in self._provider_chain():
            try:
                if used_fallback:
                    logger.info("Переключаюсь на fallback: {}", model)
                text, tokens = self._answer_from(client, model, messages)
                return LLMResult(
                    text, tokens,
                    "fallback" if used_fallback else "primary",
                    model, used_fallback,
                )
            except Exception as e:
                provider = "fallback" if used_fallback else "primary"
                logger.warning(
                    "Не удалось получить ответ через {} API, model={}: {}",
                    provider, model, e,
                )

        logger.error("Все LLM API недоступны, возвращаю технический fallback-ответ")
        return LLMResult(FALLBACK_ANSWER, 0, "unavailable", "none", True)

    def transcribe(self, audio_path: str, stt_model: str) -> str:
        """STT: аудиофайл → текст через audio.transcriptions."""
        client = self.primary
        if client is None:
            logger.error("STT API недоступен: не задан OPENAI_API_KEY для primary OpenAI API")
            return ""
        try:
            with open(audio_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model=stt_model,
                    file=f,
                    language="ru",
                    response_format="text",
                )
            return transcript.text if hasattr(transcript, "text") else str(transcript)
        except Exception as e:
            logger.error("STT API недоступен или модель {} не поддерживается: {}", stt_model, e)
            return ""

    def speak(self, text: str, tts_model: str, voice: str, output_path: str) -> str:
        """TTS: текст → аудиофайл через audio.speech."""
        client = self.primary
        if client is None:
            logger.error("TTS API недоступен: не задан OPENAI_API_KEY для primary OpenAI API")
            return ""
        try:
            response = client.audio.speech.create(
                model=tts_model,
                voice=voice,
                input=text,
            )
            response.stream_to_file(output_path)
            return output_path
        except Exception as e:
            logger.error("TTS API недоступен или модель {} не поддерживается: {}", tts_model, e)
            return ""

    def generate_image(
        self, prompt: str, model: str, output_path: str,
    ) -> str:
        """Генерация изображения через OpenAI images.generate."""
        client = self.primary
        if client is None:
            logger.error("Images API недоступен: не задан OPENAI_API_KEY для primary OpenAI API")
            return ""
        try:
            response = client.images.generate(
                model=model,
                prompt=prompt,
                size="1024x1024",
                quality="auto",
                n=1,
                output_format="png",
            )
            image_b64 = response.data[0].b64_json
            if image_b64:
                Path(output_path).write_bytes(base64.b64decode(image_b64))
                return output_path
        except Exception as e:
            logger.error("Images API недоступен или модель {} не поддерживается: {}", model, e)
        return ""

    # ── Внутренние методы ─────────────────────────────────────────────

    def _answer_from(
        self, client: OpenAI, model: str, messages: list[dict[str, Any]],
    ) -> tuple[str, int]:
        """Один ответ от провайдера. Возвращает (текст, токены)."""
        text, tokens = self._call(client, model, messages)
        return (text or FALLBACK_ANSWER), tokens

    def _call(
        self,
        client: OpenAI,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 250,
    ) -> tuple[str, int]:
        """Вызов LLM с retry через tenacity (экспоненциальная задержка)."""

        @retry(
            wait=wait_exponential(multiplier=1, min=1, max=60),
            stop=stop_after_attempt(self.settings.retry_attempts),
            retry=retry_if_exception_type((RateLimitError, APIStatusError)),
        )
        def _do() -> tuple[str, int]:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.settings.request_timeout_seconds,
            )
            text = (response.choices[0].message.content or "").strip()
            tokens = getattr(response.usage, "total_tokens", 0) if response.usage else 0
            logger.debug("LLM usage: {} | tokens={}", response.usage, tokens)
            return text, tokens

        return _do()
