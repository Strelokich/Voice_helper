"""
main.py
Точка входа. Запускает PyQt6-приложение с главным окном ассистента.

Запуск:
    python main.py
"""

from __future__ import annotations

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    from PySide6.QtWidgets import QApplication

from config.config_manager import ConfigManager
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Voice Assistant")

    config = ConfigManager()
    window = MainWindow(config)

    if config.get("general", "start_minimized", default=False):
        window.showMinimized()
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
