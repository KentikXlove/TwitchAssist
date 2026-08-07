# twitch_decapi

![version](https://img.shields.io/badge/version-0.1.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.7+-blue)

Простой клиент для получения данных о Twitch-каналах через сервис [decapi.com](https://decapi.com/twitch). Пакет предоставляет удобный Python-интерфейс для получения аватара, заголовка стрима, количества подписчиков, текущей игры и других данных без необходимости работать с официальным Twitch API.

---

## Оглавление

- [Установка](#установка)
- [Быстрый старт](#быстрый-старт)
- [API](#api)
- [Примеры](#примеры)
- [Внесение вклада](#внесение-вклада)
- [Лицензия](#лицензия)

---

## Установка

Установите пакет через pip:

```bash
pip install twitch_decapi
```

Либо скопируйте модуль вручную из репозитория:

```bash
git clone https://github.com/KentikXlove/SoursePackage.git
cd SoursePackage
```

### Зависимости

- `requests` — для выполнения HTTP-запросов

---

## Быстрый старт

```python
from packages.twitch_decapi import TwitchClient

# Создаём клиент для канала
client = TwitchClient("forsen")

# Получаем базовую информацию
print(client.get_title())  # Заголовок стрима
print(client.get_game())  # Текущая игра
print(client.get_viewers())  # Количество зрителей
print(client.get_avatar())  # URL аватара
```

---

## API

### `TwitchClient(channel: str, timeout: int = 10, user_agent: Optional[str] = None)`

Клиент для работы с Twitch через decapi.com.

| Параметр      | Тип                | Описание |
|---------------|-------------------|----------|
| `channel`     | `str`             | Имя канала (без `@`). |
| `timeout`     | `int`             | Таймаут для запросов в секундах. По умолчанию `10`. |
| `user_agent`  | `Optional[str]`   | Пользовательский User-Agent. |

### Методы

| Метод               | Возвращает     | Описание |
|---------------------|---------------|----------|
| `get_avatar()`      | `str`         | URL аватара канала. |
| `get_title()`       | `str`         | Заголовок текущего стрима (пустая строка, если оффлайн). |
| `get_uptime()`      | `str`         | Время работы стрима в формате `1h 20m` или `Offline`. |
| `get_followers()`   | `int`         | Количество подписчиков. |
| `get_game()`        | `str`         | Название текущей игры (пустая строка, если оффлайн). |
| `get_status()`      | `str`         | `online` или `offline`. |
| `get_viewers()`     | `int`         | Текущее количество зрителей (`0`, если оффлайн). |
| `get_subcount()`    | `int`         | Приблизительное количество сабов. |
| `get_custom(endpoint: str)` | `str` | Произвольный endpoint decapi (например, `"followcount"`). |

### Исключения

| Исключение              | Описание |
|-------------------------|----------|
| `TwitchDecapiError`     | Базовое исключение для всех ошибок пакета. |
| `ChannelNotFoundError`  | Канал не найден или недоступен. |
| `DecapiRequestError`    | Ошибка при выполнении запроса к decapi. |

---

## Примеры

### Получение полной информации о канале

```python
from packages.twitch_decapi import TwitchClient

client = TwitchClient("shroud")

info = {
    "avatar": client.get_avatar(),
    "title": client.get_title(),
    "game": client.get_game(),
    "status": client.get_status(),
    "viewers": client.get_viewers(),
    "followers": client.get_followers(),
    "uptime": client.get_uptime(),
}

print(info)
```

Пример вывода:

```
{
    "avatar": "https://static-cdn.jtvnw.net/jtv_user_pictures/...",
    "title": "VALORANT with friends",
    "game": "VALORANT",
    "status": "online",
    "viewers": 15234,
    "followers": 7234567,
    "uptime": "2h 45m"
}
```

### Обработка ошибок

```python
from packages.twitch_decapi import TwitchClient, ChannelNotFoundError, DecapiRequestError

client = TwitchClient("несуществующий_канал")

try:
    print(client.get_title())
except ChannelNotFoundError as e:
    print(f"Ошибка: {e}")
except DecapiRequestError as e:
    print(f"Проблема с соединением: {e}")
```

### Использование произвольного endpoint'а

```python
client = TwitchClient("xqc")

# Получить данные через произвольный endpoint
follows = client.get_custom("followcount")
print(follows)  # "1234567"
```

---

## Внесение вклада

Мы приветствуем вклад в развитие проекта!

1. Форкните репозиторий.
2. Создайте ветку для вашей функции (`git checkout -b feature/amazing-feature`).
3. Внесите изменения и добавьте тесты.
4. Убедитесь, что все тесты проходят.
5. Отправьте Pull Request.

---

## Лицензия

MIT © 2026 KentikXlove
