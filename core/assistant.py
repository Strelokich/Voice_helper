"""
assistant.py
Главный класс приложения без GUI-зависимостей: соединяет распознавание речи,
опциональное слово-активатор (wake word), синтез речи и движок команд.
GUI (ui/main_window.py) создаёт один экземпляр VoiceAssistant и подписывается
на его события через колбэки.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from core.speech_recognizer import build_recognizer, RecognizerError
from core.tts import TextToSpeech, TTSError
from core.command_engine import CommandEngine

logger = logging.getLogger("voice_assistant.assistant")


class VoiceAssistant:
    def __init__(self, config):
        self.config = config
        self.recognizer = None
        self.tts: Optional[TextToSpeech] = None
        self.command_engine: Optional[CommandEngine] = None

        # GUI-колбэки (устанавливаются извне)
        self.on_state_change: Optional[Callable[[str], None]] = None   # "listening" | "idle" | "error"
        self.on_recognized: Optional[Callable[[str], None]] = None
        self.on_partial: Optional[Callable[[str], None]] = None
        self.on_response: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_unmatched: Optional[Callable[[str], None]] = None

        self._awaiting_command = not self.config.get("general", "wake_word_enabled", default=False)

        self._init_tts()
        self.command_engine = CommandEngine(self.config, say_callback=self._speak)

    # ------------------------------------------------------------------ tts
    def _init_tts(self):
        tts_cfg = self.config.get("tts", default={})
        if not tts_cfg.get("enabled", True):
            self.tts = None
            return
        try:
            self.tts = TextToSpeech(
                voice_id=tts_cfg.get("voice_id", ""),
                rate=tts_cfg.get("rate", 175),
                volume=tts_cfg.get("volume", 1.0),
            )
        except TTSError as exc:
            logger.warning("TTS недоступен: %s", exc)
            self.tts = None

    def _speak(self, text: str):
        if not text:
            return
        if self.on_response:
            self.on_response(text)
        if self.tts:
            self.tts.say_async(text)

    # -------------------------------------------------------------- control
    def start(self) -> bool:
        try:
            self.recognizer = build_recognizer(self.config)
            self.recognizer.start(on_result=self._handle_result, on_partial=self._handle_partial)
        except RecognizerError as exc:
            logger.error("Ошибка запуска распознавания: %s", exc)
            if self.on_error:
                self.on_error(str(exc))
            return False
        except Exception as exc:  # noqa: BLE001 - любая иная ошибка при старте (например, занят микрофон)
            logger.exception("Непредвиденная ошибка запуска распознавания")
            if self.on_error:
                self.on_error(f"Не удалось запустить прослушивание: {exc}")
            return False
        if self.on_state_change:
            self.on_state_change("listening")
        return True

    def stop(self):
        if self.recognizer:
            self.recognizer.stop()
        if self.on_state_change:
            self.on_state_change("idle")

    def reload_config(self):
        """Вызывается после изменений в настройках, чтобы не требовать
        перезапуска всего приложения."""
        if self.command_engine:
            self.command_engine.reload()
        self._init_tts()
        self._awaiting_command = not self.config.get("general", "wake_word_enabled", default=False)

    # ----------------------------------------------------------- callbacks
    def _handle_partial(self, text: str):
        if self.on_partial:
            self.on_partial(text)

    def _handle_result(self, text: str):
        if self.on_recognized:
            self.on_recognized(text)

        wake_enabled = self.config.get("general", "wake_word_enabled", default=False)
        wake_word = self.config.get("general", "wake_word", default="ассистент").lower().strip()

        if wake_enabled and not self._awaiting_command:
            if wake_word in text.lower():
                self._awaiting_command = True
                self._speak("Слушаю")
            return

        handled = False
        if self.command_engine:
            handled = self.command_engine.process(text)

        if not handled and self.on_unmatched:
            self.on_unmatched(text)

        if wake_enabled:
            self._awaiting_command = False
