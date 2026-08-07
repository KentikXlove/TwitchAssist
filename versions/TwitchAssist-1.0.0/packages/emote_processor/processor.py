import os
import json
import logging
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from .exceptions import EmoteLoadError

logger = logging.getLogger(__name__)

class EmoteProcessor:
    def __init__(self, emotes_file: str = 'emotes.json', log_level: int = logging.INFO):
        self.emotes_file = emotes_file
        self._emotes_cache = {}
        self._emotes_mtime = 0
        self._logger = logging.getLogger(f"{__name__}.EmoteProcessor")
        self._logger.setLevel(log_level)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
        self._load_emotes()

    def _load_emotes(self, force: bool = False) -> Dict[str, str]:
        if not force and self._emotes_cache:
            return self._emotes_cache

        abs_path = os.path.abspath(self.emotes_file)
        if not os.path.exists(self.emotes_file):
            self._logger.warning(f"Файл со смайликами не найден: {abs_path}")
            self._emotes_cache = {}
            self._emotes_mtime = 0
            return {}

        try:
            mtime = os.path.getmtime(self.emotes_file)
            if self._emotes_cache and mtime == self._emotes_mtime and not force:
                return self._emotes_cache

            with open(self.emotes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise EmoteLoadError(f"Ожидается словарь {{ключ: URL}}, получено {type(data)}")
                self._emotes_cache = data
                self._emotes_mtime = mtime
                self._logger.info(f"Загружено {len(data)} смайликов из {abs_path}")
                return data
        except Exception as e:
            self._logger.error(f"Ошибка загрузки смайликов из {abs_path}: {e}")
            raise EmoteLoadError(f"Не удалось загрузить смайлики из {abs_path}: {e}") from e

    def reload(self) -> Dict[str, str]:
        self._logger.info("Принудительная перезагрузка смайликов")
        return self._load_emotes(force=True)

    def get_emotes(self) -> Dict[str, str]:
        return self._emotes_cache.copy()

    def process_message(self, username: str, message: str,
                        timestamp: Optional[str] = None) -> Tuple[str, List[Tuple[str, str]]]:
        if not message:
            self._logger.debug(f"[{username}] Пустое сообщение")
            return "", []

        if not self._emotes_cache:
            self._logger.debug(f"[{username}] Нет загруженных смайликов, сообщение без замен")
            return message, []

        original = message
        detected = []
        result = message

        # Сортируем ключи по убыванию длины
        keys = sorted(self._emotes_cache.keys(), key=len, reverse=True)

        for key in keys:
            url = self._emotes_cache[key]
            escaped_key = re.escape(key)

            # Определяем паттерн поиска в зависимости от типа ключа
            if re.match(r'^[a-zA-Z0-9_]+$', key):
                # Только буквенно-цифровые и подчёркивание – используем границы слова
                pattern = r'(?<![a-zA-Z0-9_])' + escaped_key + r'(?![a-zA-Z0-9_])'
            else:
                # Для спецсимволов – проверяем, что перед/после нет букв/цифр и не внутри URL
                # Разрешаем пробелы, начало/конец строки, знаки пунктуации (кроме : и /)
                pattern = r'(?<![a-zA-Z0-9:/])' + escaped_key + r'(?![a-zA-Z0-9:/])'

            # Проверяем наличие паттерна
            if re.search(pattern, result):
                replacement = f'<img class="emote" src="{url}" alt="{key}" title="{key}" />'
                result = re.sub(pattern, replacement, result)
                detected.append((key, url))

        if detected:
            self._logger.info(
                f"[{username}] Найдено {len(detected)} смайлов: {[k for k, _ in detected]} | "
                f"Сообщение: {original[:50]}{'...' if len(original) > 50 else ''}"
            )
        else:
            self._logger.debug(f"[{username}] Смайлов не найдено: {original[:50]}{'...' if len(original) > 50 else ''}")

        return result, detected

    def process_message_with_log(self, username: str, message: str,
                                 timestamp: Optional[str] = None) -> str:
        html, _ = self.process_message(username, message, timestamp)
        return html