import os
import json
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QIcon

# Определяем путь к config.json один раз (корень проекта – две папки вверх)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

class WebWindow(QMainWindow):
    def __init__(self, url: str, title: str = "Simple Web Window",
                 width: int = 800, height: int = 600,
                 icon_path: str = None, always_on_top: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(width, height)
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        self.webview = QWebEngineView()
        self.webview.setUrl(QUrl(url))
        self.setCentralWidget(self.webview)

        self._always_on_top = always_on_top
        if self._always_on_top:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Используем общий путь к конфигу
        self._config_path = CONFIG_PATH

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_config)
        self._timer.start(2000)

    def _check_config(self):
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            new_val = config.get('overlay', {}).get('always_on_top', False)
        except Exception:
            return

        if new_val != self._always_on_top:
            self._always_on_top = new_val
            if new_val:
                self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            else:
                self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.show()  # применяем новые флаги


def run_window(url: str, title: str = "Web Window",
               width: int = 800, height: int = 600,
               icon_path: str = None, always_on_top: bool = False, parent=None) -> int:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    window = WebWindow(url, title, width, height, icon_path, always_on_top, parent)
    window.show()
    return app.exec_()