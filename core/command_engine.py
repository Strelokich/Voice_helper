"""
command_engine.py
Связывает распознанный текст с зарегистрированными командами (слово/фраза ->
действие) и с AI-провайдерами (фраза-триггер -> запрос к нейросети).
Приоритет: сначала проверяются обычные команды, затем — триггеры провайдеров,
чтобы «спроси бионика включи музыку» не перехватывался буквальной командой,
если только сама команда не совпадает точнее.
"""

from __future__ import annotations

import logging
from typing import Callable, List, Optional

from actions.builtin_actions import ActionContext, get_action
from core.ai_providers import ProviderRouter

logger = logging.getLogger("voice_assistant.command_engine")


class CommandEngine:
    def __init__(self, config, say_callback: Callable[[str], None]):
        self.config = config
        self.say = say_callback
        self._context = ActionContext(say=say_callback, config=config)
        self.reload()

    def reload(self):
        """Пересобирает список команд и роутер провайдеров — вызывается после
        любого изменения настроек в GUI, без перезапуска ассистента."""
        self.commands = [c for c in self.config.get("commands", default=[]) if c.get("enabled", True)]
        self.provider_router = ProviderRouter(self.config.get("ai_providers", default=[]))

    def _match_command(self, text: str) -> Optional[dict]:
        low = text.lower().strip()
        best = None
        for cmd in self.commands:
            trigger = cmd.get("trigger", "").lower().strip()
            if not trigger:
                continue
            mode = cmd.get("match_mode", "contains")
            matched = (
                (mode == "exact" and low == trigger)
                or (mode == "startswith" and low.startswith(trigger))
                or (mode == "contains" and trigger in low)
            )
            if matched:
                # предпочитаем более длинный (специфичный) триггер
                if best is None or len(trigger) > len(best.get("trigger", "")):
                    best = cmd
        return best

    def process(self, text: str) -> bool:
        """Главная точка входа: вызывается при каждой распознанной фразе.
        Возвращает True, если фраза была обработана (команда или запрос к ИИ),
        и False, если ни одна команда/провайдер не подошли — это позволяет
        вызывающему коду (GUI) показать пользователю, что именно не совпало."""
        if not text:
            return False
        logger.info("Распознано: %s", text)

        command = self._match_command(text)
        if command:
            logger.info("Совпала команда '%s' -> действие '%s'", command.get("trigger"), command.get("action_type"))
            self._execute_command(command)
            return True

        match = self.provider_router.match(text)
        if match:
            provider, query = match
            if not query:
                self.say("Что именно спросить?")
                return True
            self._ask_provider(provider, query)
            return True

        logger.info("Ни одна команда/провайдер не совпали с фразой: %s", text)
        return False

    def _execute_command(self, command: dict) -> None:
        action_type = command.get("action_type")
        func = get_action(action_type)
        if func is None:
            self.say(f"Действие '{action_type}' не найдено.")
            return
        try:
            response = func(command.get("params", {}), self._context)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка выполнения команды %s", command.get("id"))
            response = f"Ошибка при выполнении команды: {exc}"
        if response:
            self.say(response)

    def _ask_provider(self, provider, query: str) -> None:
        def worker():
            try:
                answer = provider.ask(query)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Ошибка запроса к провайдеру")
                answer = f"Не удалось получить ответ от {provider.cfg.name}: {exc}"
            self.say(answer)

        import threading
        threading.Thread(target=worker, daemon=True).start()
