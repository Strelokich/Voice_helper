"""
tts.py
Синтез речи через pyttsx3 (офлайн, работает поверх системных голосов Windows/
Linux/macOS). Для русского языка нужен установленный в системе русский голос
(на Windows обычно есть "Irina" при установленном пакете русской речи).
"""

from __future__ import annotations

import threading
from typing import List, Optional

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


class TTSError(Exception):
    pass


class TextToSpeech:
    def __init__(self, voice_id: str = "", rate: int = 175, volume: float = 1.0):
        if not PYTTSX3_AVAILABLE:
            raise TTSError("Пакет 'pyttsx3' не установлен. Выполните: pip install pyttsx3")
        self._lock = threading.Lock()
        self.voice_id = voice_id
        self.rate = rate
        self.volume = volume
        self._engine = None
        self._init_engine()

    def _init_engine(self):
        try:
            self._engine = pyttsx3.init()
        except Exception as exc:  # noqa: BLE001 - охватывает отсутствие eSpeak/SAPI/NSSpeech в системе
            raise TTSError(
                "Не удалось инициализировать движок синтеза речи. Убедитесь, что в системе "
                "установлен голосовой движок (на Linux — eSpeak/eSpeak-ng: 'sudo apt install "
                f"espeak-ng'; на Windows и macOS обычно работает из коробки). Ошибка: {exc}"
            ) from exc
        self._engine.setProperty("rate", self.rate)
        self._engine.setProperty("volume", self.volume)
        if self.voice_id:
            self._engine.setProperty("voice", self.voice_id)

    def list_voices(self) -> List[dict]:
        voices = self._engine.getProperty("voices")
        return [{"id": v.id, "name": v.name, "languages": getattr(v, "languages", [])} for v in voices]

    def apply_settings(self, voice_id: Optional[str] = None, rate: Optional[int] = None,
                        volume: Optional[float] = None):
        if voice_id is not None:
            self.voice_id = voice_id
            self._engine.setProperty("voice", voice_id)
        if rate is not None:
            self.rate = rate
            self._engine.setProperty("rate", rate)
        if volume is not None:
            self.volume = volume
            self._engine.setProperty("volume", volume)

    def say(self, text: str, blocking: bool = True):
        """Произносит текст. По умолчанию блокирует поток вызова — используйте
        из фонового потока ассистента, а не из GUI-потока."""
        if not text:
            return
        with self._lock:
            self._engine.say(text)
            if blocking:
                self._engine.runAndWait()
            else:
                threading.Thread(target=self._engine.runAndWait, daemon=True).start()

    def say_async(self, text: str):
        threading.Thread(target=lambda: self.say(text, blocking=True), daemon=True).start()

    def stop(self):
        try:
            self._engine.stop()
        except Exception:  # noqa: BLE001
            pass
