# storage.py
import abc
import json

import os
from typing import Any

class Storage(abc.ABC):
    @abc.abstractmethod
    def read(self, key: str) -> Any:
        pass
    @abc.abstractmethod
    def write(self, key: str, value: Any):
        pass
    @abc.abstractmethod
    def delete(self, key: str):
        pass
    @abc.abstractmethod
    def exists(self, key: str) -> bool:
        pass

# -------- JSON --------
class JSONStorage(Storage):
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._data = {}
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        else:
            self._data = {}

    def _save(self):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def read(self, key: str) -> Any:
        return self._data.get(key)
    def write(self, key: str, value: Any):
        self._data[key] = value
        self._save()
    def delete(self, key: str):
        if key in self._data:
            del self._data[key]
            self._save()
    def exists(self, key: str) -> bool:
        return key in self._data

# -------- Text --------
class TextStorage(Storage):
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._data = {}
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        k, v = line.split(':', 1)
                        self._data[k] = v

    def _save(self):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            for k, v in self._data.items():
                f.write(f"{k}:{v}\n")

    def read(self, key: str) -> Any:
        return self._data.get(key)
    def write(self, key: str, value: Any):
        self._data[key] = str(value)
        self._save()
    def delete(self, key: str):
        if key in self._data:
            del self._data[key]
            self._save()
    def exists(self, key: str) -> bool:
        return key in self._data
