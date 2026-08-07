# cache.py
import time
from typing import Any, Optional

class Cache:
    def __init__(self, default_ttl: Optional[int] = None):
        self._data = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self._data:
            value, expiry = self._data[key]
            if expiry is None or expiry > time.time():
                return value
            del self._data[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        if ttl is None:
            ttl = self.default_ttl
        expiry = time.time() + ttl if ttl is not None else None
        self._data[key] = (value, expiry)

    def delete(self, key: str):
        self._data.pop(key, None)

    def clear(self):
        self._data.clear()

    def exists(self, key: str) -> bool:
        return key in self._data and (self._data[key][1] is None or self._data[key][1] > time.time())