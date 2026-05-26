"""Загрузка и сборка промптов для LLM.

Читает шаблоны промптов и few-shot примеры из файлов пакета
(``system_prompt.txt``, ``classifier_system_prompt.txt``,
``classifier_few_shots.json``, ``service_facts.txt``) и предоставляет
функции для формирования готовых списков сообщений для классификатора
и основного ассистента.
"""

from __future__ import annotations

import base64
import json
from importlib import resources
from pathlib import Path
from typing import Any


def _read_prompt_file(filename: str) -> str:
    return resources.files(__package__).joinpath(filename).read_text(encoding="utf-8").strip()


SERVICE_FACTS = _read_prompt_file("service_facts.txt")
SYSTEM_PROMPT_TEMPLATE = _read_prompt_file("system_prompt.txt")
CLASSIFIER_SYSTEM_PROMPT = _read_prompt_file("classifier_system_prompt.txt")
CLASSIFIER_FEW_SHOTS = json.loads(_read_prompt_file("classifier_few_shots.json"))


def build_system_prompt(service_name: str) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        service_name=service_name,
        service_facts=SERVICE_FACTS,
    )


def classifier_few_shot_messages() -> list[dict[str, str]]:
    return CLASSIFIER_FEW_SHOTS.copy()


def encode_image(image_path: str) -> tuple[str, str]:
    """Кодирует изображение в base64. Возвращает (base64_data, расширение)."""
    p = Path(image_path)
    ext = p.suffix.lstrip(".").lower()
    if ext == "jpg":
        ext = "jpeg"
    return base64.b64encode(p.read_bytes()).decode("utf-8"), ext


def build_answer_messages(
    system_prompt: str,
    history: list[dict[str, str]],
    user_message: str,
    image_path: str | None = None,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    if image_path:
        b64, ext = encode_image(image_path)
        content: list[dict[str, Any]] = [
            {"type": "text", "text": user_message},
            {"type": "image_url", "image_url": {
                "url": f"data:image/{ext};base64,{b64}",
                "detail": "high",
            }},
        ]
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": user_message})

    return messages


def build_classifier_messages(user_message: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT}]
    messages.extend(classifier_few_shot_messages())
    messages.append({"role": "user", "content": user_message})
    return messages
