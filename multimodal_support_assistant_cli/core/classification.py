"""Классификация пользовательских запросов и правила эскалации.

Определяет категории CloudTech, словари ключевых слов для эвристической классификации
и функцию ``should_escalate``,
которая решает, нужно ли передавать запрос живому оператору.
"""

from __future__ import annotations

from models import Category

ESCALATION_KEYWORDS = {
    "оператор",
    "специалист",
    "менеджер",
    "начальник",
    "жалоба",
    "юрист",
    "суд",
    "прокуратура",
    "роспотребнадзор",
    "срочно",
    "критично",
    "критичный",
    "critical",
    "деньги",
    "возврат",
    "компенсация",
    "утечка",
    "потеря данных",
    "удалил все",
    "полный отказ",
}

SECURITY_KEYWORDS = {
    "доступ",
    "api-ключ",
    "сертификат",
    "утечка",
    "взлом",
    "s3",
}

KUBERNETES_KEYWORDS = {
    "kubernetes",
    "k8s",
    "docker",
    "контейнер",
    "pod",
    "поды",
    "ingress",
    "crashloopbackoff",
}

DATABASE_KEYWORDS = {
    "postgresql",
    "mysql",
    "база данных",
    "бд",
    "backup",
    "бэкап",
    "репликация",
}

BILLING_KEYWORDS = {
    "счет",
    "счёт",
    "оплата",
    "тариф",
    "стоимость",
    "скидка",
}

ACCOUNT_KEYWORDS = {
    "аккаунт",
    "логин",
    "пароль",
    "2fa",
    "sso",
    "invalid credentials",
}

API_KEYWORDS = {
    "api",
    "sdk",
    "интеграция",
    "webhook",
}

PERFORMANCE_KEYWORDS = {
    "медленно",
    "таймаут",
    "timeout",
    "производительность",
    "деградация",
}

INFRASTRUCTURE_KEYWORDS = {
    "сервер",
    "сеть",
    "дата-центр",
    "инфраструктура",
    "недоступен",
}


def heuristic_classify(user_message: str) -> Category:
    text = user_message.lower()
    if any(keyword in text for keyword in ESCALATION_KEYWORDS):
        return Category.ESCALATION
    if any(keyword in text for keyword in SECURITY_KEYWORDS):
        return Category.SECURITY
    if any(keyword in text for keyword in KUBERNETES_KEYWORDS):
        return Category.KUBERNETES
    if any(keyword in text for keyword in DATABASE_KEYWORDS):
        return Category.DATABASE
    if any(keyword in text for keyword in BILLING_KEYWORDS):
        return Category.BILLING
    if any(keyword in text for keyword in ACCOUNT_KEYWORDS):
        return Category.ACCOUNT
    if any(keyword in text for keyword in API_KEYWORDS):
        return Category.API
    if any(keyword in text for keyword in PERFORMANCE_KEYWORDS):
        return Category.PERFORMANCE
    if any(keyword in text for keyword in INFRASTRUCTURE_KEYWORDS):
        return Category.INFRASTRUCTURE
    return Category.OFF_TOPIC


def should_escalate(user_message: str) -> bool:
    text = user_message.lower()
    return any(keyword in text for keyword in ESCALATION_KEYWORDS)
