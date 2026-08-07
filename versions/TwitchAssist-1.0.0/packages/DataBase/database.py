# database.py
import logging
from typing import Any, Optional
from .cache import Cache
from .storage import Storage

class Database:
    def __init__(self, storage: Storage, default_ttl: Optional[int] = None,
                 logger: Optional[logging.Logger] = None):
        self.storage = storage
        self.cache = Cache(default_ttl=default_ttl)
        self.logger = logger or logging.getLogger(__name__)
        self._default_ttl = default_ttl

    def get(self, key: str, ttl: Optional[int] = None) -> Any:
        self.logger.debug(f"Getting key: {key}")
        cached = self.cache.get(key)
        if cached is not None:
            self.logger.debug(f"Cache hit for key: {key}")
            return cached
        self.logger.debug(f"Cache miss, reading from storage")
        value = self.storage.read(key)
        if value is not None:
            self.cache.set(key, value, ttl=ttl or self._default_ttl)
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        self.logger.debug(f"Setting key: {key}")
        self.storage.write(key, value)
        self.cache.set(key, value, ttl=ttl or self._default_ttl)

    def delete(self, key: str):
        self.logger.debug(f"Deleting key: {key}")
        self.storage.delete(key)
        self.cache.delete(key)

    def exists(self, key: str) -> bool:
        self.logger.debug(f"Checking existence of key: {key}")
        if self.cache.exists(key):
            return True
        return self.storage.exists(key)

    def clear_cache(self):
        self.logger.debug("Clearing cache")
        self.cache.clear()

    def set_default_ttl(self, ttl: Optional[int]):
        self._default_ttl = ttl
        self.cache.default_ttl = ttl