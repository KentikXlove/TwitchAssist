# Twitch IRC Client

![version](https://img.shields.io/badge/version-1.0.0-blue) ![license](https://img.shields.io/badge/license-MIT-green) ![python](https://img.shields.io/badge/python-3.6+-blue)

Простой, лёгкий и независимый IRC-клиент для Twitch на Python. Подключается к любому каналу, читает сообщения чата и передаёт их в вашу callback-функцию.

---

## Оглавление

- [Установка](#установка)
- [Быстрый старт](#быстрый-старт)
- [Структура данных сообщения](#структура-данных-сообщения)
- [API](#api)
- [Примеры](#примеры)
- [Лицензия](#лицензия)

---

## Установка

Установите пакет напрямую из исходников:

```bash
git clone https://github.com/KentikXlove/SoursePackage.git
cd SoursePackage/twitch_irc
pip install -e .
```

Или просто скопируйте папку `twitch_irc` в ваш проект и импортируйте оттуда.

---

## Быстрый старт

Минимальный пример использования:

```python
from packages.twitch_irc import TwitchIRC


# Обработчик сообщений
def on_message(msg):
    print(f"[{msg['username']}] {msg['message']}")


# Создаём клиент и запускаем
client = TwitchIRC(on_message=on_message)
client.start("forsen")  # имя канала без #

# ... ваш код ...

# Остановка клиента при завершении
client.stop()
```

По умолчанию используется **анонимное подключение** — OAuth-токен не требуется.

---

## Структура данных сообщения

Ваш callback получает словарь со следующими полями:

| Поле | Тип | Описание |
|------|-----|----------|
| `username` | `str` | Имя пользователя, написавшего сообщение |
| `message` | `str` | Текст сообщения |
| `color` | `str` | HEX-цвет (например, `#ff5733`), сгенерированный из имени |
| `timestamp` | `str` | Время получения сообщения в формате ISO 8601 |
| `badges` | `list` | Список бейджей пользователя (каждый — словарь с `name` и `version`) |

Пример:

```python
{
    "username": "forsen",
    "message": "Hello, world!",
    "color": "#1a2b3c",
    "timestamp": "2026-08-02T12:34:56.789012",
    "badges": [
        {"name": "broadcaster", "version": "1"},
        {"name": "subscriber", "version": "12"}
    ]
}
```

---

## API

### `__init__(username="justinfan123", password="justinfan123", on_message=None)`

| Параметр | Тип | Описание |
|----------|-----|----------|
| `username` | `str` | Ник для подключения (по умолчанию анонимный) |
| `password` | `str` | Пароль (для анонима можно оставить как есть) |
| `on_message` | `callable` | Функция, принимающая один аргумент (словарь с сообщением) |

### `start(channel)`

- `channel` — имя канала без символа `#` (регистр не важен)
- Запускает подключение в отдельном потоке. Если клиент уже запущен, предыдущее подключение останавливается.

### `stop()`

Останавливает клиент, закрывает сокет и завершает поток.

---

## Примеры

### Авторизованное подключение

Если вам нужно авторизоваться (например, для отправки сообщений или получения других привилегий), передайте свои данные:

```python
client = TwitchIRC(
    username="your_bot",
    password="oauth:ваш_токен",
    on_message=on_message
)
```

> **Примечание:** для обычного чтения чата авторизация не требуется.

### Интеграция с веб-интерфейсом

Отправляйте сообщения чата в веб-интерфейс через Socket.IO:

```python
from packages.twitch_irc import TwitchIRC
import socketio

sio = socketio.Client()
sio.connect('http://localhost:5000')


def forward_message(msg):
    sio.emit('chat_message', msg)


client = TwitchIRC(on_message=forward_message)
client.start("my_channel")
```

---

## Логирование

Клиент использует стандартный модуль `logging` с именем `__name__`. Вы можете настроить уровень логирования и вывод:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

---

## Лицензия

MIT © 2026 KentikXlove
