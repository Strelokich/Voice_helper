"""
config_manager.py
Централизованное хранение настроек ассистента: распознавание речи, TTS,
команды и AI-провайдеры. Всё сохраняется в JSON рядом с исполняемым файлом,
чтобы GUI-настройки переживали перезапуск программы.
"""

from __future__ import annotations

import json
import os
import copy
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_data")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "general": {
        "wake_word_enabled": False,
        "wake_word": "ассистент",
        "language": "ru",
        "start_minimized": False,
    },
    "recognition": {
        # Распознавание речи работает только локально через Vosk — без
        # обращения к каким-либо облачным API распознавания речи.
        "vosk_model_path": "models/vosk-model-small-ru-0.22",
        "microphone_index": None,  # None = устройство по умолчанию
        "energy_threshold": 300,
    },
    "tts": {
        "enabled": True,
        "engine": "pyttsx3",
        "voice_id": "",       # системный голос, выбирается в настройках
        "rate": 175,
        "volume": 1.0,
    },
    "commands": [
        # Пример команд-заготовок, пользователь редактирует их в GUI
        {
            "id": "open-browser",
            "trigger": "открой браузер",
            "match_mode": "contains",   # contains | exact | startswith
            "action_type": "open_app",
            "params": {"path": "chrome"},
            "enabled": True,
        },
        {
            "id": "current-time",
            "trigger": "который час",
            "match_mode": "contains",
            "action_type": "say_time",
            "params": {},
            "enabled": True,
        },
    ],
    # Провайдеры нейросетей. type: openai | anthropic | bionicgpt | openai_compatible
    "ai_providers": [
        {
            "id": "bionic-default",
            "name": "BionicGPT",
            "type": "bionicgpt",
            "trigger": "спроси бионика",
            "base_url": "http://localhost:3000/v1",
            "api_key": "",
            "model": "default",
            "system_prompt": "Ты — голосовой ассистент. Отвечай кратко и по-русски.",
            "enabled": False,
        },
        {
            "id": "openai-default",
            "name": "OpenAI",
            "type": "openai",
            "trigger": "спроси чатжпт",
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "model": "gpt-4o-mini",
            "system_prompt": "Ты — голосовой ассистент. Отвечай кратко и по-русски.",
            "enabled": False,
        },
        {
            "id": "anthropic-default",
            "name": "Claude",
            "type": "anthropic",
            "trigger": "спроси клода",
            "base_url": "https://api.anthropic.com",
            "api_key": "",
            "model": "claude-sonnet-4-6",
            "system_prompt": "Ты — голосовой ассистент. Отвечай кратко и по-русски.",
            "enabled": False,
        },
    ],
    "appearance": {
        "theme": "purple_neon",
        "accent": "#b026ff",
        "accent_secondary": "#00e5ff",
    },
}


class ConfigManager:
    """Загружает, хранит и сохраняет настройки. Единая точка правды для всего приложения."""

    def __init__(self, path: str = CONFIG_PATH):
        self.path = path
        self._data: Dict[str, Any] = {}
        self.load()

    # ---------------------------------------------------------- persistence
    def load(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data = self._merge_defaults(loaded)
            except (json.JSONDecodeError, OSError):
                self._data = copy.deepcopy(DEFAULT_CONFIG)
        else:
            self._data = copy.deepcopy(DEFAULT_CONFIG)
            self.save()

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _merge_defaults(loaded: Dict[str, Any]) -> Dict[str, Any]:
        """Гарантирует, что после обновления программы в конфиге появятся новые ключи,
        а пользовательские данные (команды, провайдеры, ключи) не потеряются."""
        merged = copy.deepcopy(DEFAULT_CONFIG)
        for section, value in loaded.items():
            if section in merged and isinstance(merged[section], dict) and isinstance(value, dict):
                merged[section].update(value)
            else:
                merged[section] = value
        return merged

    # ---------------------------------------------------------------- data
    @property
    def data(self) -> Dict[str, Any]:
        return self._data

    def get(self, *keys, default=None):
        node = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
        return node

    def set(self, section: str, value: Any) -> None:
        self._data[section] = value
        self.save()

    def update_section(self, section: str, **kwargs) -> None:
        self._data.setdefault(section, {})
        self._data[section].update(kwargs)
        self.save()

    # ------------------------------------------------------------ commands
    def add_or_update_command(self, command: Dict[str, Any]) -> None:
        commands: List[Dict[str, Any]] = self._data.setdefault("commands", [])
        for i, c in enumerate(commands):
            if c["id"] == command["id"]:
                commands[i] = command
                self.save()
                return
        commands.append(command)
        self.save()

    def remove_command(self, command_id: str) -> None:
        self._data["commands"] = [c for c in self._data.get("commands", []) if c["id"] != command_id]
        self.save()

    # -------------------------------------------------------- ai providers
    def add_or_update_provider(self, provider: Dict[str, Any]) -> None:
        providers: List[Dict[str, Any]] = self._data.setdefault("ai_providers", [])
        for i, p in enumerate(providers):
            if p["id"] == provider["id"]:
                providers[i] = provider
                self.save()
                return
        providers.append(provider)
        self.save()

    def remove_provider(self, provider_id: str) -> None:
        self._data["ai_providers"] = [p for p in self._data.get("ai_providers", []) if p["id"] != provider_id]
        self.save()
