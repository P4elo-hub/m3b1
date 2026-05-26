"""Интерактивный CLI (REPL) для мультимодального ассистента поддержки.

Принимает пользовательский ввод, обрабатывает команды CLI (включая
мультимодальные /analyze, /voice, /voice_qa, /speak) и выводит ответ ассистента
с метаданными (категория, источник, задержка).
"""

from __future__ import annotations

import os

from config import Settings
from core.assistant import SupportAssistantApp


def main():
    settings = Settings.from_env()
    assistant = SupportAssistantApp(settings)

    print(f"=== {settings.service_name} Multimodal Support CLI ===")
    print("Команды: /clear, /clear_cache, /reset_redis_stats, /stats, /quit")
    print("Мультимодальные: /analyze <путь> [вопрос], /voice <путь> [вопрос], /voice_qa <путь> [вопрос], /speak")
    print("Генерация: /imagine <описание>")

    while True:
        try:
            user_input = input("\nВы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            return None

        if not user_input:
            continue

        # ── /analyze — анализ изображения через Vision API ──────────
        if user_input.startswith("/analyze "):
            parts = user_input[9:].strip().split(maxsplit=1)
            image_path = parts[0] if parts else ""
            question = parts[1] if len(parts) > 1 else ""
            if not image_path or not os.path.isfile(image_path):
                print("Использование: /analyze <путь к изображению> [вопрос]")
                if image_path and not os.path.isfile(image_path):
                    print(f"Файл не найден: {image_path}")
                continue
            prompt = question if question else (
                "Пользователь прислал скриншот. "
                "Определи проблему и предложи решение. "
                "Если видишь код ошибки — укажи его."
            )
            print("Анализирую изображение...")
            response = assistant.respond(prompt, image_path=image_path)
            source = "cache" if response.from_cache else response.provider
            print(f"[{response.category} | {source} | {response.latency_seconds:.2f}с]")
            print(response.text)
            continue

        # ── /voice — транскрипция аудио + ответ ─────────────────────
        if user_input.startswith("/voice "):
            parts = user_input[7:].strip().split(maxsplit=1)
            audio_path = parts[0] if parts else ""
            question = parts[1] if len(parts) > 1 else ""
            if not audio_path or not os.path.isfile(audio_path):
                print("Использование: /voice <путь к аудиофайлу> [вопрос]")
                if audio_path and not os.path.isfile(audio_path):
                    print(f"Файл не найден: {audio_path}")
                continue
            print("Распознаю речь...")
            transcript = assistant.transcribe(audio_path)
            print(f"Распознано: {transcript}")
            user_text = f"{question} {transcript}".strip() if question else transcript
            if not user_text:
                print("Не удалось распознать речь.")
                continue
            response = assistant.respond(user_text)
            source = "cache" if response.from_cache else response.provider
            print(f"[{response.category} | {source} | {response.latency_seconds:.2f}с]")
            print(response.text)
            continue

        # ── /voice_qa — голосовой вопрос → голосовой ответ одним шагом ─
        if user_input.startswith("/voice_qa "):
            parts = user_input[10:].strip().split(maxsplit=1)
            audio_path = parts[0] if parts else ""
            question = parts[1] if len(parts) > 1 else ""
            if not audio_path or not os.path.isfile(audio_path):
                print("Использование: /voice_qa <путь к аудиофайлу> [вопрос]")
                if audio_path and not os.path.isfile(audio_path):
                    print(f"Файл не найден: {audio_path}")
                continue
            print("Распознаю речь...")
            transcript = assistant.transcribe(audio_path)
            print(f"Распознано: {transcript}")
            user_text = f"{question} {transcript}".strip() if question else transcript
            if not user_text:
                print("Не удалось распознать речь.")
                continue
            response = assistant.respond(user_text)
            source = "cache" if response.from_cache else response.provider
            print(f"[{response.category} | {source} | {response.latency_seconds:.2f}с]")
            print(response.text)
            print("Генерирую аудиоответ...")
            output = assistant.speak(response.text)
            if output:
                print(f"Аудиоответ сохранён: {output}")
            else:
                print("Не удалось сгенерировать аудиоответ.")
            continue

        # ── /speak — озвучить последний ответ через TTS ─────────────
        if user_input == "/speak":
            if not assistant.history:
                print("Нет ответов для озвучивания.")
                continue
            last_answer = assistant.history[-1]["content"]
            print("Генерирую аудио...")
            output = assistant.speak(last_answer)
            if output:
                print(f"Аудио сохранено: {output}")
            else:
                print("Не удалось сгенерировать аудио.")
            continue

        # ── /imagine — генерация изображения через OpenAI ────────────
        if user_input.startswith("/imagine "):
            prompt = user_input[9:].strip()
            if not prompt:
                print("Использование: /imagine <описание изображения>")
                continue
            print("Генерирую изображение...")
            try:
                output = assistant.generate_image(prompt)
                if output:
                    print(f"Изображение сохранено: {output}")
                else:
                    print("Не удалось сгенерировать изображение.")
            except Exception as e:
                print(f"Ошибка генерации: {e}")
            continue

        # ── Служебные команды ────────────────────────────────────────
        if user_input.startswith("/"):
            command_result = assistant.handle_command(user_input)
            if command_result is None:
                print("До свидания!")
                return None
            print(command_result)
            continue

        # ── Обычный текстовый ввод ───────────────────────────────────
        response = assistant.respond(user_input)
        source = "cache" if response.from_cache else response.provider
        print(f"[{response.category} | {source} | {response.latency_seconds:.2f}с]")
        print(response.text)


if __name__ == "__main__":
    main()
