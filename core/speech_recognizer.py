"""
speech_recognizer.py
Обёртка над Vosk — офлайн распознавание речи на русском языке с потоковым
прослушиванием микрофона. Работает полностью локально, без интернета и без
сторонних облачных API распознавания речи.

Модель для русского языка скачивается один раз с
https://alphacephei.com/vosk/models и указывается в настройках.
"""

from __future__ import annotations

import json
import queue
import threading
from typing import Callable, Optional

try:
    import vosk
    import sounddevice as sd
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False


class RecognizerError(Exception):
    pass


class BaseRecognizer:
    """Общий интерфейс: on_result(text) вызывается при каждой финальной фразе."""

    def start(self, on_result: Callable[[str], None], on_partial: Optional[Callable[[str], None]] = None):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def is_running(self) -> bool:
        raise NotImplementedError


class VoskRecognizer(BaseRecognizer):
    """Непрерывное офлайн-распознавание речи на русском языке через Vosk."""

    def __init__(self, model_path: str, sample_rate: int = 16000, device_index: Optional[int] = None):
        if not VOSK_AVAILABLE:
            raise RecognizerError(
                "Пакеты 'vosk' и 'sounddevice' не установлены. Выполните: pip install vosk sounddevice"
            )
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.device_index = device_index
        self._model: Optional["vosk.Model"] = None
        self._q: "queue.Queue" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._stream = None

    def _load_model(self):
        if self._model is None:
            try:
                self._model = vosk.Model(self.model_path)
            except Exception as exc:  # noqa: BLE001
                raise RecognizerError(
                    f"Не удалось загрузить Vosk-модель по пути '{self.model_path}'. "
                    f"Скачайте русскую модель с https://alphacephei.com/vosk/models "
                    f"и укажите путь к распакованной папке в настройках. Ошибка: {exc}"
                ) from exc

    def _audio_callback(self, indata, frames, time_info, status):  # noqa: D401, ANN001
        self._q.put(bytes(indata))

    def start(self, on_result: Callable[[str], None], on_partial: Optional[Callable[[str], None]] = None):
        self._load_model()
        recognizer = vosk.KaldiRecognizer(self._model, self.sample_rate)
        recognizer.SetWords(False)
        self._running.set()

        def worker():
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=8000,
                dtype="int16",
                channels=1,
                device=self.device_index,
                callback=self._audio_callback,
            ):
                while self._running.is_set():
                    try:
                        data = self._q.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            on_result(text)
                    elif on_partial is not None:
                        partial = json.loads(recognizer.PartialResult())
                        p_text = partial.get("partial", "").strip()
                        if p_text:
                            on_partial(p_text)

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def is_running(self) -> bool:
        return self._running.is_set()

    @staticmethod
    def list_microphones():
        if not VOSK_AVAILABLE:
            return []
        devices = sd.query_devices()
        return [
            {"index": i, "name": d["name"]}
            for i, d in enumerate(devices)
            if d.get("max_input_channels", 0) > 0
        ]


def build_recognizer(config) -> BaseRecognizer:
    """Фабрика: создаёт распознаватель на основе текущих настроек (только Vosk)."""
    rec_cfg = config.get("recognition", default={})
    return VoskRecognizer(
        model_path=rec_cfg.get("vosk_model_path", "models/vosk-model-small-ru-0.22"),
        device_index=rec_cfg.get("microphone_index"),
    )
