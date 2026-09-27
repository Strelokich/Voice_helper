"""
ai_providers.py
Гибкая система подключения нейросетей. Каждый провайдер настраивается в GUI:
имя, тип, base_url, api_key, модель и триггер-фраза, по которой распознанная
речь маршрутизируется именно к этому провайдеру.

Поддерживаемые типы "из коробки":
  - "bionicgpt"         — self-hosted BionicGPT, отдаёт OpenAI-совместимый API
  - "openai"             — OpenAI (ChatGPT) API
  - "anthropic"           — Claude API
  - "openai_compatible"  — любой сторонний провайдер с OpenAI-совместимым API
                             (LocalAI, OpenRouter, Together, LM Studio и т.д.)

Благодаря такой структуре добавление нового стороннего провайдера, у которого
API совместим с OpenAI (а таких большинство), не требует нового кода —
достаточно завести запись в настройках с type="openai_compatible" и своим
base_url.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import urllib.request
import urllib.error


class ProviderError(Exception):
    pass


@dataclass
class ProviderConfig:
    id: str
    name: str
    type: str
    trigger: str
    base_url: str
    api_key: str
    model: str
    system_prompt: str = "Ты — голосовой ассистент. Отвечай кратко и по-русски."
    enabled: bool = True

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ProviderConfig":
        return ProviderConfig(
            id=d.get("id", ""),
            name=d.get("name", ""),
            type=d.get("type", "openai_compatible"),
            trigger=d.get("trigger", ""),
            base_url=d.get("base_url", ""),
            api_key=d.get("api_key", ""),
            model=d.get("model", ""),
            system_prompt=d.get("system_prompt", "Ты — голосовой ассистент. Отвечай кратко и по-русски."),
            enabled=d.get("enabled", True),
        )


def _http_post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ProviderError(f"HTTP {exc.code} от {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"Не удалось подключиться к {url}: {exc.reason}") from exc


class BaseAIProvider:
    """Общий интерфейс: ask(text) -> ответ нейросети одной строкой."""

    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg

    def ask(self, prompt: str) -> str:
        raise NotImplementedError

    def test_connection(self) -> bool:
        try:
            self.ask("Привет! Ответь одним словом: 'работает'.")
            return True
        except ProviderError:
            return False


class OpenAICompatibleProvider(BaseAIProvider):
    """Покрывает OpenAI, BionicGPT (OpenAI-совместимый API) и любой другой
    сторонний сервис, реализующий стандарт /v1/chat/completions."""

    def ask(self, prompt: str) -> str:
        url = self.cfg.base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"
        payload = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": self.cfg.system_prompt},
                {"role": "user", "content": prompt},
            ],
        }
        result = _http_post_json(url, headers, payload)
        try:
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Неожиданный формат ответа от {self.cfg.name}: {result}") from exc


class AnthropicProvider(BaseAIProvider):
    """Claude API (api.anthropic.com/v1/messages)."""

    def ask(self, prompt: str) -> str:
        url = self.cfg.base_url.rstrip("/") + "/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.cfg.api_key,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": self.cfg.model,
            "max_tokens": 1024,
            "system": self.cfg.system_prompt,
            "messages": [{"role": "user", "content": prompt}],
        }
        result = _http_post_json(url, headers, payload)
        try:
            blocks = result["content"]
            text_parts = [b["text"] for b in blocks if b.get("type") == "text"]
            return " ".join(text_parts).strip()
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Неожиданный формат ответа от {self.cfg.name}: {result}") from exc


_PROVIDER_CLASSES = {
    "openai": OpenAICompatibleProvider,
    "bionicgpt": OpenAICompatibleProvider,
    "openai_compatible": OpenAICompatibleProvider,
    "anthropic": AnthropicProvider,
}


def create_provider(cfg_dict: Dict[str, Any]) -> BaseAIProvider:
    cfg = ProviderConfig.from_dict(cfg_dict)
    cls = _PROVIDER_CLASSES.get(cfg.type, OpenAICompatibleProvider)
    return cls(cfg)


class ProviderRouter:
    """Хранит все включённые провайдеры и находит нужный по триггер-фразе
    в начале распознанной команды. Например: 'спроси бионика какая погода'
    -> провайдер 'BionicGPT', запрос 'какая погода'."""

    def __init__(self, provider_configs: list[Dict[str, Any]]):
        self.providers = []
        for cfg in provider_configs:
            if cfg.get("enabled") and cfg.get("trigger"):
                self.providers.append((cfg["trigger"].lower().strip(), create_provider(cfg)))
        # Сортируем по длине триггера по убыванию, чтобы более длинные и
        # специфичные фразы matched раньше более коротких.
        self.providers.sort(key=lambda t: len(t[0]), reverse=True)

    def match(self, text: str) -> Optional[tuple[BaseAIProvider, str]]:
        low = text.lower().strip()
        for trigger, provider in self.providers:
            if low.startswith(trigger):
                remainder = text[len(trigger):].strip(" ,.:-")
                return provider, remainder
        return None
