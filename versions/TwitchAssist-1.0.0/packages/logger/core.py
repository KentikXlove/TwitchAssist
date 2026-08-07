import logging
import os
from datetime import datetime
from typing import Optional, Union

# Регистрируем кастомный уровень SYSTEMERROR (45)
SYSTEMERROR_LEVELNO = 45
logging.addLevelName(SYSTEMERROR_LEVELNO, "SYSTEMERROR")

class Logger:
    """
    Простой и гибкий логгер с записью в файл, имя которого содержит дату/время.
    Поддерживает стандартные уровни + systemerror.
    """
    def __init__(
        self,
        name: Optional[str] = None,
        log_dir: str = "logs",
        filename_prefix: str = "log",
        use_timestamp: bool = True,
        level: Union[str, int] = logging.DEBUG,
        console_output: bool = False,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
    ):
        """
        :param name: имя логгера (по умолчанию - корневой)
        :param log_dir: директория для хранения логов (создаётся, если не существует)
        :param filename_prefix: префикс имени файла (добавляется метка времени)
        :param use_timestamp: если True, в имя файла добавляется текущие дата+время;
                              если False, используется только префикс (файл перезаписывается при каждом запуске)
        :param level: уровень логирования (по умолчанию DEBUG)
        :param console_output: дублировать ли сообщения в консоль (stderr)
        :param fmt: строка формата сообщения (по умолчанию: "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        :param datefmt: формат времени (по умолчанию: "%Y-%m-%d %H:%M:%S")
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        # Формируем имя файла
        if use_timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{filename_prefix}_{timestamp}.log" if filename_prefix else f"{timestamp}.log"
        else:
            filename = f"{filename_prefix}.log" if filename_prefix else "app.log"
        self.filepath = os.path.join(log_dir, filename)

        # Настраиваем логгер
        self.logger = logging.getLogger(name or __name__)
        self.logger.setLevel(self._parse_level(level))

        # Удаляем старые хендлеры, чтобы избежать дублирования при повторной инициализации
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Файловый хендлер
        file_handler = logging.FileHandler(self.filepath, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # все сообщения идут в файл, но уровень логгера фильтрует выше

        # Форматтер
        if fmt is None:
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        if datefmt is None:
            datefmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(fmt, datefmt)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Консольный хендлер (опционально)
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # Сохраняем путь к файлу для справки
        self._filepath = self.filepath

    @staticmethod
    def _parse_level(level: Union[str, int]) -> int:
        """Преобразует строковое представление уровня в числовое."""
        if isinstance(level, int):
            return level
        level_upper = level.upper()
        if level_upper == "SYSTEMERROR":
            return SYSTEMERROR_LEVELNO
        return getattr(logging, level_upper, logging.DEBUG)

    # ---------- Методы логирования ----------
    def debug(self, msg: str, *args, **kwargs) -> None:
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self.logger.warning(msg, *args, **kwargs)

    def warn(self, msg: str, *args, **kwargs) -> None:
        """Синоним warning."""
        self.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        self.logger.critical(msg, *args, **kwargs)

    def fatal(self, msg: str, *args, **kwargs) -> None:
        """Синоним critical."""
        self.critical(msg, *args, **kwargs)

    def systemerror(self, msg: str, *args, **kwargs) -> None:
        """Логирует системную ошибку (уровень SYSTEMERROR)."""
        self.logger.log(SYSTEMERROR_LEVELNO, msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        """Логирует сообщение с уровнем ERROR и добавляет информацию об исключении (если есть)."""
        self.logger.exception(msg, *args, **kwargs)

    def log(self, level: Union[str, int], msg: str, *args, **kwargs) -> None:
        """Логирование с произвольным уровнем."""
        level_num = self._parse_level(level)
        self.logger.log(level_num, msg, *args, **kwargs)

    # ---------- Утилиты ----------
    def set_level(self, level: Union[str, int]) -> None:
        """Изменяет уровень логирования."""
        self.logger.setLevel(self._parse_level(level))

    def get_filepath(self) -> str:
        """Возвращает полный путь к текущему лог-файлу."""
        return self._filepath

    def get_logger(self) -> logging.Logger:
        """Возвращает оригинальный объект logging.Logger для расширенных операций."""
        return self.logger

    def __repr__(self) -> str:
        return f"<Logger {self.logger.name} (file={self._filepath})>"