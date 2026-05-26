"""Модели данных приложения.

Все dataclass-ы и type alias-ы собраны в одном месте.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Category(str, Enum):
    BILLING = "billing"
    INFRASTRUCTURE = "infrastructure"
    KUBERNETES = "kubernetes"
    DATABASE = "database"
    SECURITY = "security"
    API = "api"
    PERFORMANCE = "performance"
    ACCOUNT = "account"
    OFF_TOPIC = "off-topic"

    # Старые категории оставлены для совместимости с эвристикой и эскалацией.
    FAQ = "faq"
    TECHNICAL = "technical"
    COMPLAINT = "complaint"
    ESCALATION = "escalation"


@dataclass
class ClassificationResult:
    category: Category
    priority: str = "unknown"
    summary: str = ""
    entities: dict[str, Any] = field(default_factory=lambda: {
        "services": [],
        "error_codes": [],
        "environment": "unknown",
    })
    requires_immediate_escalation: bool = False
    confidence: float = 0.0
    source: str = "unknown"

    def as_log_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "priority": self.priority,
            "summary": self.summary,
            "entities": self.entities,
            "requires_immediate_escalation": self.requires_immediate_escalation,
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass
class SessionStats:
    total_queries: int = 0
    escalations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_tokens: int = 0
    llm_calls: int = 0


@dataclass
class LLMResult:
    text: str
    tokens: int
    provider: str
    model: str
    used_fallback: bool


@dataclass
class AssistantResponse:
    text: str
    category: Category
    from_cache: bool
    latency_seconds: float
    provider: str
    model: str
    used_fallback: bool
