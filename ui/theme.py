"""
theme.py
Тёмно-фиолетовая неоновая тема для всего интерфейса на PyQt6/PySide6.
Цвета вынесены в константы, чтобы акцент можно было менять из настроек
(appearance.accent / appearance.accent_secondary в конфиге) без правки QSS.
"""

from __future__ import annotations

try:
    from PyQt6.QtGui import QColor
    from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget
except ImportError:  # pragma: no cover - позволяет импортировать модуль без PyQt для тестов
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget


# Базовая палитра
BG_DARK = "#0b0014"          # почти чёрный с фиолетовым подтоном — фон окна
BG_PANEL = "#150029"         # фон панелей/карточек
BG_PANEL_LIGHT = "#1f0740"   # фон полей ввода, hover-состояний
BORDER = "#3a1466"           # тонкие границы
ACCENT = "#b026ff"           # основной неоново-фиолетовый
ACCENT_2 = "#00e5ff"         # неоново-голубой (вторичный акцент)
ACCENT_PINK = "#ff2ec4"      # неоново-розовый (ошибки/важное)
TEXT_PRIMARY = "#f1e9ff"
TEXT_SECONDARY = "#9d84c9"
SUCCESS = "#39ff8a"
DANGER = "#ff3860"


def build_stylesheet(accent: str = ACCENT, accent2: str = ACCENT_2) -> str:
    return f"""
    * {{
        font-family: 'Segoe UI', 'Rubik', sans-serif;
        font-size: 13px;
        color: {TEXT_PRIMARY};
    }}

    QMainWindow, QDialog, QWidget#root {{
        background-color: {BG_DARK};
    }}

    QWidget {{
        background-color: transparent;
    }}

    /* ---------- Панели / карточки ---------- */
    QFrame#card, QGroupBox {{
        background-color: {BG_PANEL};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 12px;
    }}

    QGroupBox {{
        margin-top: 18px;
        font-weight: 600;
        color: {accent2};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 6px;
    }}

    /* ---------- Вкладки настроек ---------- */
    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-radius: 12px;
        background-color: {BG_PANEL};
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: {BG_PANEL};
        color: {TEXT_SECONDARY};
        padding: 8px 18px;
        margin-right: 4px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        border: 1px solid {BORDER};
        border-bottom: none;
    }}
    QTabBar::tab:selected {{
        color: {BG_DARK};
        background-color: {accent};
        font-weight: 600;
    }}
    QTabBar::tab:hover:!selected {{
        color: {accent2};
    }}

    /* ---------- Кнопки ---------- */
    QPushButton {{
        background-color: {BG_PANEL_LIGHT};
        color: {TEXT_PRIMARY};
        border: 1px solid {accent};
        border-radius: 10px;
        padding: 8px 16px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {accent};
        color: {BG_DARK};
    }}
    QPushButton:pressed {{
        background-color: {accent2};
        border-color: {accent2};
        color: {BG_DARK};
    }}
    QPushButton:disabled {{
        color: {TEXT_SECONDARY};
        border-color: {BORDER};
        background-color: {BG_PANEL};
    }}
    QPushButton#dangerButton {{
        border-color: {DANGER};
    }}
    QPushButton#dangerButton:hover {{
        background-color: {DANGER};
        color: {TEXT_PRIMARY};
    }}
    QPushButton#primaryButton {{
        background-color: {accent};
        color: {BG_DARK};
    }}
    QPushButton#primaryButton:hover {{
        background-color: {accent2};
        border-color: {accent2};
    }}

    /* ---------- Поля ввода ---------- */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {BG_PANEL_LIGHT};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px 10px;
        selection-background-color: {accent};
        selection-color: {BG_DARK};
    }}
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
        border: 1px solid {accent2};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {BG_PANEL};
        border: 1px solid {accent};
        selection-background-color: {accent};
        selection-color: {BG_DARK};
        outline: none;
    }}

    /* ---------- Таблицы (команды / провайдеры) ---------- */
    QTableWidget {{
        background-color: {BG_PANEL};
        gridline-color: {BORDER};
        border: 1px solid {BORDER};
        border-radius: 10px;
    }}
    QHeaderView::section {{
        background-color: {BG_PANEL_LIGHT};
        color: {accent2};
        padding: 6px;
        border: none;
        border-bottom: 2px solid {accent};
        font-weight: 600;
    }}
    QTableWidget::item:selected {{
        background-color: {accent};
        color: {BG_DARK};
    }}

    /* ---------- Переключатели / чекбоксы ---------- */
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1px solid {accent};
        background-color: {BG_PANEL_LIGHT};
    }}
    QCheckBox::indicator:checked {{
        background-color: {accent};
    }}

    /* ---------- Слайдеры ---------- */
    QSlider::groove:horizontal {{
        height: 4px;
        background: {BORDER};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {accent};
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    QSlider::sub-page:horizontal {{
        background: {accent2};
        border-radius: 2px;
    }}

    /* ---------- Скроллбары ---------- */
    QScrollBar:vertical {{
        background: {BG_DARK};
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {accent};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0;
    }}

    /* ---------- Лог / чат ---------- */
    QListWidget#chatLog {{
        background-color: {BG_PANEL};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 6px;
    }}
    QListWidget#chatLog::item {{
        padding: 6px;
    }}

    QLabel#titleLabel {{
        font-size: 20px;
        font-weight: 700;
        color: {accent2};
    }}
    QLabel#subtitleLabel {{
        color: {TEXT_SECONDARY};
    }}
    QStatusBar {{
        background-color: {BG_PANEL};
        color: {TEXT_SECONDARY};
        border-top: 1px solid {BORDER};
    }}
    """


def apply_glow(widget: "QWidget", color: str = ACCENT, radius: int = 30, offset: int = 0) -> QGraphicsDropShadowEffect:
    """Добавляет неоновое свечение вокруг виджета (кнопки, орб-индикатора и т.д.)."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setColor(QColor(color))
    effect.setBlurRadius(radius)
    effect.setOffset(offset, offset)
    widget.setGraphicsEffect(effect)
    return effect
