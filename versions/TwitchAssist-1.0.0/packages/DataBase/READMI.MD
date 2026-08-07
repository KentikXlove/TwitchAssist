# DataBase

![version](https://img.shields.io/badge/version-1.0.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![status](https://img.shields.io/badge/status-stable-brightgreen)
![python](https://img.shields.io/badge/python-3.6%2B-blue)

**DataBase** — это легковесная Python-библиотека для работы с key-value хранилищами с поддержкой кэширования. Пакет предоставляет единый интерфейс для различных типов хранилищ (JSON, текстовые файлы, SQLite) и встроенный TTL-кэш для ускорения операций чтения.

---

## Оглавление

- [Установка](#установка)
- [Быстрый старт](#быстрый-старт)
- [API](#api)
- [Примеры](#примеры)
- [Внесение вклада](#внесение-вклада)
- [Лицензия](#лицензия)
- [Поддержка](#поддержка)

---

## Установка

Склонируйте репозиторий и установите пакет:

```bash
git clone https://github.com/KentikXlove/SoursePackage.git
cd SoursePackage/DataBase
```

Пакет не требует внешних зависимостей, кроме стандартной библиотеки Python 3.6+.

Для использования в проекте просто скопируйте папку `DataBase` в ваш проект или добавьте путь к ней в `PYTHONPATH`.

---

## Быстрый старт

Пример использования с JSON-хранилищем:

```python
from packages.DataBase import Database, JSONStorage

# Создаём хранилище в файле data.json
storage = JSONStorage("data.json")
db = Database(storage, default_ttl=60)  # кэш на 60 секунд

# Запись и чтение
db.set("user:1", {"name": "Alice", "age": 30})
user = db.get("user:1")
print(user)  # {'name': 'Alice', 'age': 30}

# Проверка существования ключа
print(db.exists("user:1"))  # True

# Удаление
db.delete("user:1")
```

---

## API

### `Database`

Основной класс, объединяющий хранилище и кэш.

```python
Database(storage: Storage, default_ttl: Optional[int] = None, logger: Optional[logging.Logger] = None)
```

**Параметры:**
- `storage` — экземпляр класса-хранилища (`JSONStorage`, `TextStorage`, `SQLiteStorage`).
- `default_ttl` — время жизни кэша в секундах по умолчанию (опционально).
- `logger` — экземпляр логгера для отладки (опционально).

**Методы:**

| Метод | Описание |
|-------|----------|
| `get(key: str, ttl: Optional[int] = None) -> Any` | Получить значение по ключу. Если ключ есть в кэше — возвращает из кэша, иначе читает из хранилища и кэширует. |
| `set(key: str, value: Any, ttl: Optional[int] = None)` | Записать значение в хранилище и кэш. |
| `delete(key: str)` | Удалить ключ из хранилища и кэша. |
| `exists(key: str) -> bool` | Проверить существование ключа (сначала проверяет кэш, затем хранилище). |
| `clear_cache()` | Очистить весь кэш. |
| `set_default_ttl(ttl: Optional[int])` | Установить время жизни кэша по умолчанию. |

---

### Хранилища

Все хранилища наследуют абстрактный класс `Storage` и реализуют методы `read`, `write`, `delete`, `exists`.

#### `JSONStorage`

```python
JSONStorage(filepath: str)
```

Хранит данные в JSON-файле. Поддерживает любые сериализуемые JSON типы.

#### `TextStorage`

```python
TextStorage(filepath: str)
```

Хранит данные в текстовом файле в формате `ключ:значение`. Все значения преобразуются в строки.

#### `SQLiteStorage`

```python
SQLiteStorage(filepath: str)
```

Хранит данные в SQLite-базе данных с таблицей `data(key TEXT PRIMARY KEY, value TEXT)`.

---

### `Cache`

Внутренний TTL-кэш. Обычно не требуется использовать напрямую.

```python
Cache(default_ttl: Optional[int] = None)
```

**Методы:** `get`, `set`, `delete`, `clear`, `exists`.

---

### Исключения

- `DatabaseError` — базовое исключение пакета. Возникает при ошибках работы с хранилищем.

---

## Примеры

### Пример 1: Использование с SQLite

```python
from packages.DataBase import Database, SQLiteStorage

storage = SQLiteStorage("app.db")
db = Database(storage, default_ttl=300)

db.set("config:theme", "dark")
db.set("config:language", "ru")

print(db.get("config:theme"))  # dark
print(db.exists("config:lang"))  # False
```

### Пример 2: Работа с текстовым хранилищем

```python
from packages.DataBase import Database, TextStorage

storage = TextStorage("settings.txt")
db = Database(storage)

db.set("host", "localhost")
db.set("port", "8080")

print(db.get("host"))  # localhost
```

### Пример 3: Ручное управление кэшем

```python
from packages.DataBase import Database, JSONStorage

storage = JSONStorage("data.json")
db = Database(storage, default_ttl=10)

db.set("temp", 42)
print(db.get("temp"))  # 42, читает из кэша

# Очистка кэша
db.clear_cache()
print(db.get("temp"))  # 42, читает из хранилища (и снова кэширует)
```




---

## Внесение вклада

Мы приветствуем ваш вклад в развитие проекта!

1. Форкните репозиторий.
2. Создайте ветку для вашей функции (`git checkout -b feature/amazing-feature`).
3. Внесите изменения и убедитесь, что код работает.
4. Оформите Pull Request с описанием ваших изменений.

---



## Поддержка

Если вы нашли ошибку или у вас есть предложения, создайте [Issue](https://github.com/KentikXlove/SoursePackage/issues) в репозитории.