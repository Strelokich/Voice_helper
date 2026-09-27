"""
settings_window.py
Подробное окно настроек с вкладками:
  1. Общие       — язык, слово-активатор, поведение при запуске
  2. Распознавание — офлайн (Vosk) / онлайн, микрофон, путь к модели
  3. Голос (TTS) — системный голос, скорость, громкость
  4. Команды      — таблица "фраза -> действие", добавление/редактирование/удаление
  5. Нейросети    — таблица провайдеров (BionicGPT, OpenAI, Claude, свои),
                     тест соединения
"""

from __future__ import annotations

import uuid

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QWidget,
        QLabel, QLineEdit, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
        QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
        QTextEdit, QSlider, QFileDialog, QAbstractItemView,
    )
except ImportError:  # pragma: no cover
    from PySide6.QtCore import Qt, Signal as pyqtSignal
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QWidget,
        QLabel, QLineEdit, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
        QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
        QTextEdit, QSlider, QFileDialog, QAbstractItemView,
    )

from actions.builtin_actions import ACTION_REGISTRY
from core.ai_providers import create_provider, ProviderError
from core.speech_recognizer import VoskRecognizer
from core.tts import TextToSpeech, TTSError


# ---------------------------------------------------------------- helpers
def _row_text(table: QTableWidget, row: int, col: int) -> str:
    item = table.item(row, col)
    return item.text() if item else ""


# ============================================================== COMMAND DIALOG
class CommandEditDialog(QDialog):
    def __init__(self, command: dict | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Команда")
        self.setMinimumWidth(420)
        self.command = command.copy() if command else {
            "id": str(uuid.uuid4()),
            "trigger": "",
            "match_mode": "contains",
            "action_type": "say_text",
            "params": {},
            "enabled": True,
        }

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.trigger_edit = QLineEdit(self.command.get("trigger", ""))
        form.addRow("Фраза-триггер:", self.trigger_edit)

        self.match_combo = QComboBox()
        self.match_combo.addItems(["contains", "exact", "startswith"])
        self.match_combo.setCurrentText(self.command.get("match_mode", "contains"))
        form.addRow("Тип совпадения:", self.match_combo)

        self.action_combo = QComboBox()
        self.action_combo.addItems(list(ACTION_REGISTRY.keys()))
        self.action_combo.setCurrentText(self.command.get("action_type", "say_text"))
        self.action_combo.currentTextChanged.connect(self._update_param_fields)
        form.addRow("Действие:", self.action_combo)

        self.params_container = QVBoxLayout()
        form.addRow("Параметры:", QWidget())
        layout.addLayout(form)
        layout.addLayout(self.params_container)

        self.enabled_check = QCheckBox("Включена")
        self.enabled_check.setChecked(self.command.get("enabled", True))
        layout.addWidget(self.enabled_check)

        self._param_widgets: dict[str, QLineEdit] = {}
        self._update_param_fields(self.action_combo.currentText())

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch(1)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    # Разные действия требуют разных параметров — показываем нужные поля динамически
    PARAM_SCHEMA = {
        "open_app": ["path"],
        "open_url": ["url"],
        "run_command": ["command"],
        "say_text": ["text"],
        "system_volume": ["direction (up/down/mute)"],
        "say_time": [],
        "say_date": [],
    }

    def _update_param_fields(self, action_type: str):
        while self.params_container.count():
            item = self.params_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._param_widgets = {}

        fields = self.PARAM_SCHEMA.get(action_type, [])
        existing_params = self.command.get("params", {})
        for field_label in fields:
            key = field_label.split(" ")[0]
            row = QHBoxLayout()
            row.addWidget(QLabel(field_label + ":"))
            edit = QLineEdit(str(existing_params.get(key, "")))
            row.addWidget(edit)
            self._param_widgets[key] = edit
            wrapper = QWidget()
            wrapper.setLayout(row)
            self.params_container.addWidget(wrapper)

    def get_command(self) -> dict:
        self.command["trigger"] = self.trigger_edit.text().strip()
        self.command["match_mode"] = self.match_combo.currentText()
        self.command["action_type"] = self.action_combo.currentText()
        self.command["enabled"] = self.enabled_check.isChecked()
        self.command["params"] = {k: w.text() for k, w in self._param_widgets.items()}
        return self.command


# ============================================================= PROVIDER DIALOG
class ProviderEditDialog(QDialog):
    TYPE_PRESETS = {
        "bionicgpt": {"base_url": "http://localhost:3000/v1", "model": "default"},
        "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
        "anthropic": {"base_url": "https://api.anthropic.com", "model": "claude-sonnet-4-6"},
        "openai_compatible": {"base_url": "https://your-provider.example.com/v1", "model": "model-name"},
    }

    def __init__(self, provider: dict | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Нейросеть-провайдер")
        self.setMinimumWidth(460)
        self.provider = provider.copy() if provider else {
            "id": str(uuid.uuid4()),
            "name": "",
            "type": "openai_compatible",
            "trigger": "",
            "base_url": "",
            "api_key": "",
            "model": "",
            "system_prompt": "Ты — голосовой ассистент. Отвечай кратко и по-русски.",
            "enabled": True,
        }

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(self.provider.get("name", ""))
        form.addRow("Название:", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(list(self.TYPE_PRESETS.keys()))
        self.type_combo.setCurrentText(self.provider.get("type", "openai_compatible"))
        self.type_combo.currentTextChanged.connect(self._apply_preset)
        form.addRow("Тип (протокол):", self.type_combo)

        self.trigger_edit = QLineEdit(self.provider.get("trigger", ""))
        self.trigger_edit.setPlaceholderText("например: спроси бионика")
        form.addRow("Фраза-активатор:", self.trigger_edit)

        self.base_url_edit = QLineEdit(self.provider.get("base_url", ""))
        form.addRow("Base URL:", self.base_url_edit)

        self.api_key_edit = QLineEdit(self.provider.get("api_key", ""))
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API-ключ:", self.api_key_edit)

        self.model_edit = QLineEdit(self.provider.get("model", ""))
        form.addRow("Модель:", self.model_edit)

        self.system_prompt_edit = QTextEdit(self.provider.get("system_prompt", ""))
        self.system_prompt_edit.setFixedHeight(70)
        form.addRow("Системный промпт:", self.system_prompt_edit)

        self.enabled_check = QCheckBox("Провайдер включён")
        self.enabled_check.setChecked(self.provider.get("enabled", True))

        layout.addLayout(form)
        layout.addWidget(self.enabled_check)

        self.test_result_label = QLabel("")
        layout.addWidget(self.test_result_label)

        btn_row = QHBoxLayout()
        test_btn = QPushButton("Проверить соединение")
        test_btn.clicked.connect(self._test_connection)
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(test_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _apply_preset(self, type_name: str):
        preset = self.TYPE_PRESETS.get(type_name, {})
        if not self.base_url_edit.text():
            self.base_url_edit.setText(preset.get("base_url", ""))
        if not self.model_edit.text():
            self.model_edit.setText(preset.get("model", ""))

    def _test_connection(self):
        cfg = self.get_provider()
        try:
            provider = create_provider(cfg)
            ok = provider.test_connection()
            if ok:
                self.test_result_label.setText("✅ Соединение успешно установлено")
            else:
                self.test_result_label.setText("⚠ Провайдер не ответил корректно")
        except ProviderError as exc:
            self.test_result_label.setText(f"❌ {exc}")
        except Exception as exc:  # noqa: BLE001
            self.test_result_label.setText(f"❌ Неожиданная ошибка: {exc}")

    def get_provider(self) -> dict:
        self.provider["name"] = self.name_edit.text().strip()
        self.provider["type"] = self.type_combo.currentText()
        self.provider["trigger"] = self.trigger_edit.text().strip()
        self.provider["base_url"] = self.base_url_edit.text().strip()
        self.provider["api_key"] = self.api_key_edit.text().strip()
        self.provider["model"] = self.model_edit.text().strip()
        self.provider["system_prompt"] = self.system_prompt_edit.toPlainText().strip()
        self.provider["enabled"] = self.enabled_check.isChecked()
        return self.provider


# =================================================================== MAIN WINDOW
class SettingsWindow(QDialog):
    settings_saved = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Настройки ассистента")
        self.resize(760, 620)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_general_tab(), "Общие")
        self.tabs.addTab(self._build_recognition_tab(), "Распознавание")
        self.tabs.addTab(self._build_tts_tab(), "Голос")
        self.tabs.addTab(self._build_commands_tab(), "Команды")
        self.tabs.addTab(self._build_providers_tab(), "Нейросети")

        bottom = QHBoxLayout()
        save_btn = QPushButton("Сохранить и применить")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_all)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.close)
        bottom.addStretch(1)
        bottom.addWidget(close_btn)
        bottom.addWidget(save_btn)
        layout.addLayout(bottom)

    # ---------------------------------------------------------------- general
    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        general = self.config.get("general", default={})

        self.wake_enabled_check = QCheckBox("Требовать слово-активатор перед командой")
        self.wake_enabled_check.setChecked(general.get("wake_word_enabled", False))
        form.addRow(self.wake_enabled_check)

        self.wake_word_edit = QLineEdit(general.get("wake_word", "ассистент"))
        form.addRow("Слово-активатор:", self.wake_word_edit)

        self.start_minimized_check = QCheckBox("Запускать свёрнутым")
        self.start_minimized_check.setChecked(general.get("start_minimized", False))
        form.addRow(self.start_minimized_check)

        return w

    # ----------------------------------------------------------- recognition
    def _build_recognition_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        rec = self.config.get("recognition", default={})

        info = QLabel(
            "Распознавание речи работает полностью локально через Vosk — "
            "без интернета и без обращения к сторонним облачным сервисам."
        )
        info.setWordWrap(True)
        info.setObjectName("subtitleLabel")
        form.addRow(info)

        model_row = QHBoxLayout()
        self.vosk_path_edit = QLineEdit(rec.get("vosk_model_path", ""))
        browse_btn = QPushButton("Обзор…")
        browse_btn.clicked.connect(self._browse_vosk_model)
        model_row.addWidget(self.vosk_path_edit)
        model_row.addWidget(browse_btn)
        model_wrapper = QWidget()
        model_wrapper.setLayout(model_row)
        form.addRow("Папка модели Vosk:", model_wrapper)

        hint = QLabel(
            "Скачайте русскую модель на https://alphacephei.com/vosk/models "
            "(например vosk-model-small-ru-0.22) и укажите путь к распакованной папке."
        )
        hint.setWordWrap(True)
        hint.setObjectName("subtitleLabel")
        form.addRow(hint)

        self.energy_spin = QSpinBox()
        self.energy_spin.setRange(50, 4000)
        self.energy_spin.setValue(rec.get("energy_threshold", 300))
        form.addRow("Порог чувствительности:", self.energy_spin)

        return w

    def _browse_vosk_model(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку модели Vosk")
        if path:
            self.vosk_path_edit.setText(path)

    # ------------------------------------------------------------------- tts
    def _build_tts_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        tts_cfg = self.config.get("tts", default={})

        self.tts_enabled_check = QCheckBox("Озвучивать ответы")
        self.tts_enabled_check.setChecked(tts_cfg.get("enabled", True))
        form.addRow(self.tts_enabled_check)

        self.voice_combo = QComboBox()
        self.voice_combo.addItem("Системный голос по умолчанию", "")
        try:
            probe = TextToSpeech()
            for v in probe.list_voices():
                self.voice_combo.addItem(v["name"], v["id"])
        except TTSError:
            pass
        current_voice = tts_cfg.get("voice_id", "")
        idx = self.voice_combo.findData(current_voice)
        if idx >= 0:
            self.voice_combo.setCurrentIndex(idx)
        form.addRow("Голос:", self.voice_combo)

        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(80, 350)
        self.rate_spin.setValue(tts_cfg.get("rate", 175))
        form.addRow("Скорость речи:", self.rate_spin)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(tts_cfg.get("volume", 1.0) * 100))
        form.addRow("Громкость:", self.volume_slider)

        return w

    # -------------------------------------------------------------- commands
    def _build_commands_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.commands_table = QTableWidget(0, 4)
        self.commands_table.setHorizontalHeaderLabels(["Фраза", "Действие", "Включена", "ID"])
        self.commands_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.commands_table.setColumnHidden(3, True)
        self.commands_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.commands_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.commands_table)

        self._reload_commands_table()

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self._add_command)
        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self._edit_command)
        del_btn = QPushButton("Удалить")
        del_btn.setObjectName("dangerButton")
        del_btn.clicked.connect(self._delete_command)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        return w

    def _reload_commands_table(self):
        commands = self.config.get("commands", default=[])
        self.commands_table.setRowCount(0)
        for cmd in commands:
            row = self.commands_table.rowCount()
            self.commands_table.insertRow(row)
            self.commands_table.setItem(row, 0, QTableWidgetItem(cmd.get("trigger", "")))
            self.commands_table.setItem(row, 1, QTableWidgetItem(cmd.get("action_type", "")))
            self.commands_table.setItem(row, 2, QTableWidgetItem("да" if cmd.get("enabled", True) else "нет"))
            self.commands_table.setItem(row, 3, QTableWidgetItem(cmd.get("id", "")))

    def _add_command(self):
        dlg = CommandEditDialog(None, parent=self)
        if dlg.exec():
            self.config.add_or_update_command(dlg.get_command())
            self._reload_commands_table()

    def _edit_command(self):
        row = self.commands_table.currentRow()
        if row < 0:
            return
        cmd_id = _row_text(self.commands_table, row, 3)
        cmd = next((c for c in self.config.get("commands", default=[]) if c["id"] == cmd_id), None)
        if not cmd:
            return
        dlg = CommandEditDialog(cmd, parent=self)
        if dlg.exec():
            self.config.add_or_update_command(dlg.get_command())
            self._reload_commands_table()

    def _delete_command(self):
        row = self.commands_table.currentRow()
        if row < 0:
            return
        cmd_id = _row_text(self.commands_table, row, 3)
        if QMessageBox.question(self, "Удаление", "Удалить эту команду?") == QMessageBox.StandardButton.Yes:
            self.config.remove_command(cmd_id)
            self._reload_commands_table()

    # -------------------------------------------------------------- providers
    def _build_providers_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        info = QLabel(
            "Каждый провайдер активируется своей голосовой фразой, например "
            "«спроси бионика», «спроси чатжпт», «спроси клода». Можно добавить "
            "любое количество провайдеров, включая сторонние OpenAI-совместимые API."
        )
        info.setWordWrap(True)
        info.setObjectName("subtitleLabel")
        layout.addWidget(info)

        self.providers_table = QTableWidget(0, 5)
        self.providers_table.setHorizontalHeaderLabels(["Название", "Тип", "Триггер", "Включён", "ID"])
        self.providers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.providers_table.setColumnHidden(4, True)
        self.providers_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.providers_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.providers_table)

        self._reload_providers_table()

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self._add_provider)
        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self._edit_provider)
        del_btn = QPushButton("Удалить")
        del_btn.setObjectName("dangerButton")
        del_btn.clicked.connect(self._delete_provider)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        return w

    def _reload_providers_table(self):
        providers = self.config.get("ai_providers", default=[])
        self.providers_table.setRowCount(0)
        for p in providers:
            row = self.providers_table.rowCount()
            self.providers_table.insertRow(row)
            self.providers_table.setItem(row, 0, QTableWidgetItem(p.get("name", "")))
            self.providers_table.setItem(row, 1, QTableWidgetItem(p.get("type", "")))
            self.providers_table.setItem(row, 2, QTableWidgetItem(p.get("trigger", "")))
            self.providers_table.setItem(row, 3, QTableWidgetItem("да" if p.get("enabled", True) else "нет"))
            self.providers_table.setItem(row, 4, QTableWidgetItem(p.get("id", "")))

    def _add_provider(self):
        dlg = ProviderEditDialog(None, parent=self)
        if dlg.exec():
            self.config.add_or_update_provider(dlg.get_provider())
            self._reload_providers_table()

    def _edit_provider(self):
        row = self.providers_table.currentRow()
        if row < 0:
            return
        p_id = _row_text(self.providers_table, row, 4)
        provider = next((p for p in self.config.get("ai_providers", default=[]) if p["id"] == p_id), None)
        if not provider:
            return
        dlg = ProviderEditDialog(provider, parent=self)
        if dlg.exec():
            self.config.add_or_update_provider(dlg.get_provider())
            self._reload_providers_table()

    def _delete_provider(self):
        row = self.providers_table.currentRow()
        if row < 0:
            return
        p_id = _row_text(self.providers_table, row, 4)
        if QMessageBox.question(self, "Удаление", "Удалить этого провайдера?") == QMessageBox.StandardButton.Yes:
            self.config.remove_provider(p_id)
            self._reload_providers_table()

    # ----------------------------------------------------------------- save
    def _save_all(self):
        self.config.update_section(
            "general",
            wake_word_enabled=self.wake_enabled_check.isChecked(),
            wake_word=self.wake_word_edit.text().strip() or "ассистент",
            start_minimized=self.start_minimized_check.isChecked(),
        )
        self.config.update_section(
            "recognition",
            vosk_model_path=self.vosk_path_edit.text().strip(),
            energy_threshold=self.energy_spin.value(),
        )
        self.config.update_section(
            "tts",
            enabled=self.tts_enabled_check.isChecked(),
            voice_id=self.voice_combo.currentData() or "",
            rate=self.rate_spin.value(),
            volume=self.volume_slider.value() / 100.0,
        )
        self.settings_saved.emit()
        QMessageBox.information(self, "Готово", "Настройки сохранены и применены.")
