import requests
import logging
import time
from typing import Optional, Dict, Any
from .exceptions import ChannelNotFoundError, DecapiRequestError

logger = logging.getLogger(__name__)


class TwitchClient:
    """
    Клиент для работы с Twitch через decapi.me.
    """
    BASE_URL = "https://decapi.me/twitch"

    def __init__(self, channel: str, timeout: int = 10, user_agent: Optional[str] = None):
        self.channel = channel.strip().lower()
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            # --- НОВЫЕ ЗАГОЛОВКИ ДЛЯ ОТКЛЮЧЕНИЯ КЭША ---
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        })

    def _request(self, endpoint: str) -> str:
        """Выполняет GET-запрос и возвращает текст ответа."""
        url = f"{self.BASE_URL}/{endpoint}/{self.channel}"
        # Добавляем параметр с текущим временем, чтобы обойти кэширование на уровне прокси/CDN
        params = {'_': int(time.time())}
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as e:
            raise DecapiRequestError(f"Ошибка подключения к decapi: {e}") from e

        if response.status_code == 404:
            raise ChannelNotFoundError(f"Канал '{self.channel}' не найден или недоступен")
        if response.status_code != 200:
            raise DecapiRequestError(
                f"Неожиданный статус {response.status_code}: {response.text[:100]}"
            )
        return response.text.strip()

    # ---- Основные методы ----
    def get_avatar(self) -> str:
        return self._request("avatar")

    def get_title(self) -> str:
        return self._request("title")

    def get_uptime(self) -> str:
        return self._request("uptime")

    def get_followers(self) -> int:
        raw = self._request("followcount")
        try:
            return int(raw)
        except ValueError:
            raise DecapiRequestError(f"Некорректное число подписчиков: {raw}")

    def get_game(self) -> str:
        return self._request("game")

    def get_status(self) -> str:
        return self._request("status")

    def get_viewers(self) -> int:
        raw = self._request("viewercount")
        try:
            return int(raw)
        except ValueError:
            return 0  # если вернулось что-то нечисловое

    def get_subcount(self) -> int:
        raw = self._request("subcount")
        try:
            return int(raw)
        except ValueError:
            return 0

    # ---- Пакетное получение с обработкой ошибок ----
    def get_all(self) -> Dict[str, Any]:
        """
        Возвращает словарь со всеми основными данными.
        Если какой-то запрос упал, поле заполняется значением по умолчанию,
        а ошибка логируется и сохраняется в список '_errors'.
        """
        result = {}
        errors = []

        requests_spec = [
            ("avatar_url", self.get_avatar, ""),
            ("title", self.get_title, ""),
            ("uptime", self.get_uptime, "Offline"),
            ("followers", self.get_followers, 0),
            ("game", self.get_game, ""),
            ("status", self.get_status, "offline"),
            ("viewers", self.get_viewers, 0),
            ("subcount", self.get_subcount, 0),
        ]

        for key, method, default in requests_spec:
            try:
                result[key] = method()
            except Exception as e:
                result[key] = default
                errors.append(f"{key}: {e}")
                logger.warning(f"Ошибка получения {key} для канала {self.channel}: {e}")

        result['_errors'] = errors
        if errors:
            logger.info(f"Частичные данные для {self.channel}, ошибки: {len(errors)}")
        return result