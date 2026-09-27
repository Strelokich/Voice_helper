"""
builtin_actions.py
Набор готовых действий, которые можно привязать к голосовой команде.
Каждое действие — функция вида (params: dict, context: ActionContext) -> str,
возвращающая текст, который ассистент произнесёт в ответ (может быть пустым).
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass
class ActionContext:
    """Прокидывается в каждое действие: доступ к TTS, конфигу и т.д."""
    say: Callable[[str], None]
    config: object


def action_open_app(params: dict, ctx: ActionContext) -> str:
    """params: {"path": "chrome"} или {"path": "C:/Program Files/App/app.exe"}"""
    path = params.get("path", "")
    if not path:
        return "Не указан путь к приложению."
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", path])
        else:
            subprocess.Popen([path])
        return ""
    except Exception as exc:  # noqa: BLE001
        return f"Не удалось запустить приложение: {exc}"


def action_open_url(params: dict, ctx: ActionContext) -> str:
    """params: {"url": "https://youtube.com"}"""
    url = params.get("url", "")
    if not url:
        return "Не указан адрес сайта."
    webbrowser.open(url)
    return ""


def action_run_command(params: dict, ctx: ActionContext) -> str:
    """params: {"command": "shutdown /s /t 60"} — произвольная shell-команда."""
    command = params.get("command", "")
    if not command:
        return "Команда не задана."
    try:
        subprocess.Popen(command, shell=True)
        return ""
    except Exception as exc:  # noqa: BLE001
        return f"Ошибка выполнения команды: {exc}"


def action_say_time(params: dict, ctx: ActionContext) -> str:
    now = datetime.datetime.now()
    return f"Сейчас {now.strftime('%H:%M')}"


def action_say_date(params: dict, ctx: ActionContext) -> str:
    now = datetime.datetime.now()
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    return f"Сегодня {now.day} {months[now.month - 1]} {now.year} года"


def action_say_text(params: dict, ctx: ActionContext) -> str:
    """Просто произносит заданный в настройках фиксированный текст."""
    return params.get("text", "")


def action_system_volume(params: dict, ctx: ActionContext) -> str:
    """params: {"direction": "up"|"down"|"mute"} — управление громкостью (Windows,
    через nircmd, если установлен; на Linux — через amixer)."""
    direction = params.get("direction", "")
    try:
        if sys.platform.startswith("win"):
            steps = {"up": "changesysvolume 5000", "down": "changesysvolume -5000", "mute": "mutesysvolume 2"}
            subprocess.Popen(f"nircmd.exe {steps.get(direction, '')}", shell=True)
        else:
            steps = {"up": "5%+", "down": "5%-", "mute": "toggle"}
            subprocess.Popen(f"amixer -D pulse sset Master {steps.get(direction, '0%')}", shell=True)
        return ""
    except Exception as exc:  # noqa: BLE001
        return f"Не удалось изменить громкость: {exc}"


# Реестр: action_type -> функция. Дополнительные действия можно
# регистрировать через register_action() из любого места программы,
# например из плагина.
ACTION_REGISTRY: Dict[str, Callable[[dict, ActionContext], str]] = {
    "open_app": action_open_app,
    "open_url": action_open_url,
    "run_command": action_run_command,
    "say_time": action_say_time,
    "say_date": action_say_date,
    "say_text": action_say_text,
    "system_volume": action_system_volume,
}


def register_action(name: str, func: Callable[[dict, ActionContext], str]) -> None:
    ACTION_REGISTRY[name] = func


def get_action(name: str) -> Optional[Callable[[dict, ActionContext], str]]:
    return ACTION_REGISTRY.get(name)
