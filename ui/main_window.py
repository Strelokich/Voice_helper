"""
main_window.py
Главное окно: неоновый орб-индикатор состояния, кнопка запуска/остановки
прослушивания, лента распознанных фраз и ответов, кнопка перехода к
подробным настройкам.
"""

from __future__ import annotations

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QListWidget, QListWidgetItem, QStatusBar, QSizePolicy, QMessageBox,
    )
except ImportError:  # pragma: no cover
    from PySide6.QtCore import Qt, Signal as pyqtSignal
    from PySide6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QListWidget, QListWidgetItem, QStatusBar, QSizePolicy, QMessageBox,
    )

from ui.theme import build_stylesheet, apply_glow, ACCENT, ACCENT_2
from ui.widgets.neon_orb import NeonOrb
from ui.settings_window import SettingsWindow
from core.assistant import VoiceAssistant


class MainWindow(QMainWindow):
    # Сигналы для безопасной передачи данных из фонового потока ассистента в GUI-поток
    sig_recognized = pyqtSignal(str)
    sig_response = pyqtSignal(str)
    sig_state = pyqtSignal(str)
    sig_error = pyqtSignal(str)
    sig_unmatched = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.assistant = VoiceAssistant(config)
        self._wire_assistant()

        self.setWindowTitle("Голосовой ассистент")
        self.resize(920, 640)
        self.setStyleSheet(build_stylesheet(
            config.get("appearance", "accent", default=ACCENT),
            config.get("appearance", "accent_secondary", default=ACCENT_2),
        ))

        self._build_ui()

        self.sig_recognized.connect(self._on_recognized)
        self.sig_response.connect(self._on_response)
        self.sig_state.connect(self._on_state)
        self.sig_error.connect(self._on_error)
        self.sig_unmatched.connect(self._on_unmatched)

    # ------------------------------------------------------------- wiring
    def _wire_assistant(self):
        self.assistant.on_recognized = lambda text: self.sig_recognized.emit(text)
        self.assistant.on_response = lambda text: self.sig_response.emit(text)
        self.assistant.on_state_change = lambda state: self.sig_state.emit(state)
        self.assistant.on_error = lambda msg: self.sig_error.emit(msg)
        self.assistant.on_unmatched = lambda text: self.sig_unmatched.emit(text)

    # ------------------------------------------------------------------ ui
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Заголовок + кнопка настроек
        header = QHBoxLayout()
        title = QLabel("Голосовой ассистент")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Скажите команду или обратитесь к подключённой нейросети")
        subtitle.setObjectName("subtitleLabel")
        title_box = QVBoxLayout()
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)

        self.settings_btn = QPushButton("⚙ Настройки")
        self.settings_btn.clicked.connect(self._open_settings)
        header.addWidget(self.settings_btn)
        layout.addLayout(header)

        # Орб + кнопка старт/стоп
        center = QVBoxLayout()
        center.setSpacing(20)
        self.orb = NeonOrb()
        apply_glow(self.orb, color=ACCENT_2, radius=60)
        orb_row = QHBoxLayout()
        orb_row.addStretch(1)
        orb_row.addWidget(self.orb)
        orb_row.addStretch(1)
        center.addLayout(orb_row)

        self.toggle_btn = QPushButton("▶  Начать слушать")
        self.toggle_btn.setObjectName("primaryButton")
        self.toggle_btn.setFixedWidth(240)
        self.toggle_btn.clicked.connect(self._toggle_listening)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.toggle_btn)
        btn_row.addStretch(1)
        center.addLayout(btn_row)

        self.state_label = QLabel("Ассистент остановлен")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setObjectName("subtitleLabel")
        center.addWidget(self.state_label)

        layout.addLayout(center)

        # Лог диалога
        log_label = QLabel("История")
        log_label.setObjectName("subtitleLabel")
        layout.addWidget(log_label)

        self.chat_log = QListWidget()
        self.chat_log.setObjectName("chatLog")
        self.chat_log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.chat_log, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к запуску")

        self._listening = False

    # ------------------------------------------------------------- actions
    def _toggle_listening(self):
        if self._listening:
            self.assistant.stop()
            self.toggle_btn.setText("▶  Начать слушать")
            self._listening = False
        else:
            started = self.assistant.start()
            if started:
                self.toggle_btn.setText("■  Остановить")
                self._listening = True
            # если старт не удался, on_error уже показал причину — кнопку не трогаем

    def _open_settings(self):
        dlg = SettingsWindow(self.config, parent=self)
        dlg.settings_saved.connect(self._on_settings_saved)
        dlg.exec()
        # Команды и провайдеры уже сохраняются в конфиг сразу при добавлении/
        # редактировании в таблицах — подхватываем их в работающем ассистенте,
        # даже если пользователь закрыл окно кнопкой «Закрыть», а не «Сохранить».
        self.assistant.reload_config()

    def _on_settings_saved(self):
        self.assistant.reload_config()
        self.status_bar.showMessage("Настройки применены", 3000)

    # ----------------------------------------------------------- callbacks
    def _add_log(self, text: str, is_user: bool):
        item = QListWidgetItem(("🗣  " if is_user else "🤖  ") + text)
        self.chat_log.addItem(item)
        self.chat_log.scrollToBottom()

    def _on_recognized(self, text: str):
        self._add_log(text, is_user=True)

    def _on_response(self, text: str):
        self._add_log(text, is_user=False)
        self.orb.set_state("speaking")

    def _on_state(self, state: str):
        self.orb.set_state(state)
        labels = {
            "listening": "Слушаю…",
            "idle": "Ассистент остановлен",
            "error": "Ошибка — см. статус-бар",
        }
        self.state_label.setText(labels.get(state, state))

    def _on_unmatched(self, text: str):
        # Не озвучиваем и не пишем в чат (иначе при обычной речи без слова-активатора
        # это было бы навязчиво) — только тихая подсказка в статус-баре для отладки.
        self.status_bar.showMessage(f"Ни одна команда/провайдер не совпали с фразой: «{text}»", 6000)

    def _on_error(self, message: str):
        self.status_bar.showMessage(message, 10000)
        self.orb.set_state("error")
        self.toggle_btn.setText("▶  Начать слушать")
        self._listening = False
        QMessageBox.warning(self, "Не удалось запустить прослушивание", message)

    def closeEvent(self, event):  # noqa: N802
        self.assistant.stop()
        super().closeEvent(event)
