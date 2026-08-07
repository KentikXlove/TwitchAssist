# web_window

![version](https://img.shields.io/badge/version-1.0.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.6%2B-blue)

**web_window** — это простой и лёгкий пакет для создания окон с встроенным браузером на основе **PyQt5** и **QtWebEngine**. Позволяет быстро открыть любое веб-приложение или сайт в отдельном окне с минимальным кодом.

---

## 📋 Оглавление

- [Установка](#-установка)
- [Быстрый старт](#-быстрый-старт)
- [API](#-api)
- [Примеры](#-примеры)
- [Внесение вклада](#-внесение-вклада)
- [Лицензия](#-лицензия)

---

## 📦 Установка

### Требования

- Python 3.6 или выше
- PyQt5
- PyQtWebEngine

### Установка через pip

```bash
pip install PyQt5 PyQtWebEngine
```

### Установка из репозитория

```bash
git clone https://github.com/KentikXlove/SoursePackage.git
cd SoursePackage
pip install .
```

Или просто скопируйте папку `web_window` в ваш проект.

---

## 🚀 Быстрый старт

Самый простой способ использовать пакет — вызвать функцию `run_window()`:

```python
from packages.web_window import run_window

run_window("https://example.com", title="Мой браузер")
```

Это откроет окно с указанным URL и запустит цикл обработки событий Qt.

---

## 📖 API

### `WebWindow`

Класс окна с встроенным браузером на основе `QMainWindow` и `QWebEngineView`.

```python
WebWindow(url: str, title: str = "Simple Web Window", width: int = 800, height: int = 600, icon_path: str = None, parent=None)
```

**Параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `url` | `str` | URL для открытия (обязательный). |
| `title` | `str` | Заголовок окна. По умолчанию: `"Simple Web Window"`. |
| `width` | `int` | Ширина окна в пикселях. По умолчанию: `800`. |
| `height` | `int` | Высота окна в пикселях. По умолчанию: `600`. |
| `icon_path` | `str` | Путь к файлу иконки (PNG, ICO и т.д.). Если не указан — иконка не устанавливается. |
| `parent` | `QWidget` | Родительское окно. Если указано — окно будет дочерним. |

---

### `run_window`

Утилитарная функция для быстрого запуска окна. Создаёт экземпляр `QApplication`, если он ещё не существует, показывает окно и запускает event loop.

```python
run_window(url: str, title: str = "Simple Web Window", width: int = 800, height: int = 600, icon_path: str = None, parent=None) -> int
```

**Параметры:**  
Те же, что и у `WebWindow`.

**Возвращает:**  
Код завершения приложения (`int`).

---

## 💡 Примеры

### Пример 1: Базовое использование

```python
from packages.web_window import run_window

run_window("https://www.python.org", title="Python.org")
```

### Пример 2: С пользовательскими размерами и иконкой

```python
from packages.web_window import run_window

run_window(
    url="https://github.com",
    title="GitHub",
    width=1024,
    height=768,
    icon_path="icon.png"
)
```

### Пример 3: Использование класса `WebWindow` в существующем приложении

```python
import sys
from PyQt5.QtWidgets import QApplication
from packages.web_window import WebWindow

app = QApplication(sys.argv)

window = WebWindow(
    url="https://yandex.ru",
    title="Яндекс",
    width=1200,
    height=800
)
window.show()

sys.exit(app.exec_())
```

---

## 🤝 Внесение вклада

Мы приветствуем вклад в развитие проекта!

1. Форкните репозиторий.
2. Создайте ветку для вашей функции (`git checkout -b feature/amazing-feature`).
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`).
4. Отправьте изменения в ваш форк (`git push origin feature/amazing-feature`).
5. Откройте Pull Request.

---



© 2026 [KentikXlove](https://github.com/KentikXlove)