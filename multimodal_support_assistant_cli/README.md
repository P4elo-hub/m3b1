# Support Assistant CLI

CLI-приложение помощника техподдержки. Проект умеет классифицировать обращения, отвечать через LLM, кешировать ответы в Redis, работать с fallback-провайдером Ollama, логировать полный результат классификации и выполнять голосовой пайплайн: аудио-вопрос → LLM → аудио-ответ.

## Структура

```text
support_assistant_cli/
  cli.py                  # точка входа
  models.py               # все dataclass-ы и type alias-ы
  core/
    assistant.py          # сценарий диалога и команды CLI
    classification.py     # категории и правила эскалации
  infrastructure/
    cache.py              # Redis-кеш
    llm.py                # retry (tenacity) + fallback для LLM
  prompts/
    loader.py             # загрузка prompt-файлов
    system_prompt.txt
    classifier_system_prompt.txt
    classifier_few_shots.json
    service_facts.txt
```

## Возможности

- `System prompt` в формате РРФО: роль, правила, факты, ограничения
- `Few-shot` в классификаторе: 5 примеров
- `Retry`: tenacity с экспоненциальной задержкой (RateLimitError, APIStatusError)
- `Fallback`: primary OpenAI API → fallback Ollama
- `Кеширование`: Redis-кеш (TTL по умолчанию 1 час)
- `CLI`: `/clear`, `/clear_cache`, `/reset_redis_stats`, `/stats`, `/quit`, `/voice_qa`
- `Логирование`: loguru в файл `assistant.log`
- `Все провайдеры` через OpenAI-совместимый API (OpenAI, Groq, OpenRouter, Ollama)
- `История`: последние 10 сообщений для контекста
- `Классификация`: `billing`, `infrastructure`, `kubernetes`, `database`, `security`, `api`, `performance`, `account`, `off-topic`
- `Эскалация`: только по локальным ключевым словам до обращения к LLM
- `Голосовой пайплайн`: `/voice_qa` распознаёт аудио, получает ответ LLM и сохраняет TTS-файл
- `Устойчивость`: если Redis недоступен, приложение продолжает работать без кеша
- `STT/TTS`: Whisper и TTS работают только через primary OpenAI API

## Что изменилось относительно первой версии

- Добавлена команда `/voice_qa <путь> [вопрос]`: полный сценарий голосовой вопрос → текстовый ответ → `../response.mp3`.
- STT-модель по умолчанию заменена на `whisper-1`.
- Добавлен `.env` для настройки OpenAI, Ollama, Redis, STT/TTS и image generation.
- Добавлен `requirements.txt` и `install_dependencies.sh` для установки зависимостей.
- Добавлен `.gitignore`, чтобы не коммитить `.env`, `.venv`, логи и сгенерированные mp3.
- Классификатор переведён на CloudTech-формат JSON: категория, приоритет, summary, services, error codes, environment, confidence.
- В лог теперь пишется полный JSON классификации и полный ответ модели без обрезки.
- `requires_immediate_escalation` больше не берётся напрямую из ответа классификатора. Приложение выставляет его само: по локальным словам эскалации или если итоговый ответ не содержит данных для решения.
- Эскалация теперь проверяется до LLM по локальному списку слов: `оператор`, `специалист`, `менеджер`, `срочно`, `деньги`, `критично`, `юрист`, `утечка`, `потеря данных` и др.
- Если primary OpenAI API недоступен или упирается в лимиты, приложение переключается на Ollama (`gemma3:1b`).
- Если Redis не запущен, приложение не падает, а просто работает без кеширования.


## Запуск

Рекомендуемый запуск из корня проекта:

```bash
cd /Users/ivan/Downloads/ai-tools-and-links-main/m2_b6
source .venv/bin/activate
cd multimodal_support_assistant_cli
python cli.py
```

Redis нужен для кеширования. Если Redis не запущен, приложение продолжит работать без кеша.

```bash
brew services start redis
redis-cli ping
```

Для сохранения кеша после перезапуска Redis включите RDB или AOF (`appendonly yes` в `redis.conf`).

Для fallback через Ollama:

```bash
brew install ollama
ollama serve
ollama pull gemma3:1b
```

## Переменные окружения

### Основной провайдер
- `OPENAI_API_KEY` — API-ключ (OpenAI, Groq, OpenRouter и т.д.)
- `OPENAI_BASE_URL` — base URL, обычно не указывается для OpenAI
- `SUPPORT_PRIMARY_MODEL` — модель, по умолчанию `gpt-4o-mini`
- `SUPPORT_CLASSIFIER_MODEL` — модель классификатора, по умолчанию `gpt-4o-mini`

### Fallback-провайдер
- `FALLBACK_API_KEY` — API-ключ fallback (по умолчанию `ollama`)
- `FALLBACK_BASE_URL` — base URL fallback (по умолчанию `http://localhost:11434/v1`)
- `FALLBACK_MODEL` — модель fallback (по умолчанию `gemma3:1b`)

### Redis
- `REDIS_HOST` — хост Redis, по умолчанию `localhost`
- `REDIS_PORT` — порт Redis, по умолчанию `6379`
- `REDIS_TTL` — время жизни кеша в секундах, по умолчанию `3600`

### Прочее
- `SUPPORT_SERVICE_NAME` — имя сервиса, по умолчанию `CloudBox`
- `SUPPORT_STT_MODEL` — модель распознавания речи, по умолчанию `whisper-1`
- `SUPPORT_TTS_MODEL` — модель озвучки, по умолчанию `tts-1`
- `SUPPORT_TTS_VOICE` — голос TTS, по умолчанию `nova`
- `IMAGEGEN_MODEL` — модель генерации изображений, по умолчанию `gpt-image-1`

Если OpenAI API недоступен, текстовые ответы и классификация могут перейти на Ollama. Голосовые функции `/voice`, `/voice_qa`, `/speak` требуют рабочий OpenAI API, потому что Ollama не поддерживает Whisper/TTS endpoints.

## Быстрый сценарий проверки

1. `Планируем миграцию с AWS RDS на ваше решение. Интересует совместимость с PostgreSQL 15, поддержка TimescaleDB и стоимость для объема 500GB.`
2. Повторите тот же вопрос и проверьте `cache` в строке статуса.
3. `У нас прод-кластер K8s перестал принимать входящий трафик после обновления ingress-nginx.`
4. `Позовите оператора, это срочно`
5. `/stats`
6. `/clear_cache`
7. `/voice_qa ../request_too_large.mp3` — голосовой вопрос → ответ в `../response.mp3`
