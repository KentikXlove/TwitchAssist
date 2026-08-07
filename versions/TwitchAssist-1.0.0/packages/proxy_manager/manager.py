import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class ProxyManager:
    """
    Управление прокси для исходящих запросов.
    Хранит строку прокси и предоставляет словарь для requests.
    """
    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url

    def get_proxies(self) -> Optional[Dict[str, str]]:
        """Возвращает словарь для requests, если прокси задан."""
        if not self.proxy_url:
            return None
        # Для HTTP/HTTPS
        if self.proxy_url.startswith(('http://', 'https://')):
            return {
                'http': self.proxy_url,
                'https': self.proxy_url
            }
        # Для SOCKS (если установлена поддержка)
        elif self.proxy_url.startswith(('socks4://', 'socks5://')):
            return {
                'http': self.proxy_url,
                'https': self.proxy_url
            }
        else:
            logger.warning(f"Неизвестный формат прокси: {self.proxy_url}")
            return None

    def update(self, proxy_url: Optional[str]):
        self.proxy_url = proxy_url