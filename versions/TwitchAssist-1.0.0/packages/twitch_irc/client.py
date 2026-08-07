import socket
import threading
import hashlib
import logging
from datetime import datetime
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)

class TwitchIRC:
    """
    Простой IRC-клиент для Twitch.
    Подключается к каналу, слушает сообщения и вызывает callback.
    """

    def __init__(
        self,
        username: str = "justinfan123",
        password: str = "justinfan123",
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        :param username: ник для подключения (по умолчанию анонимный)
        :param password: пароль (для анонима не нужен)
        :param on_message: функция, принимающая словарь с полями:
                           username, message, color, timestamp, badges
        """
        self.username = username
        self.password = password
        self.on_message = on_message

        self.sock: Optional[socket.socket] = None
        self.channel: Optional[str] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False

    def start(self, channel: str) -> None:
        """Запускает подключение к каналу (в отдельном потоке)."""
        if self.running:
            self.stop()
        self.channel = channel.lower()
        self.running = True
        self.thread = threading.Thread(target=self._connect, daemon=True)
        self.thread.start()
        logger.info(f"IRC-клиент запущен для канала #{self.channel}")

    def stop(self) -> None:
        """Останавливает клиент и закрывает сокет."""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        logger.info("IRC-клиент остановлен")

    def _connect(self) -> None:
        """Основной цикл подключения и чтения данных."""
        try:
            self.sock = socket.socket()
            self.sock.settimeout(2)
            self.sock.connect(("irc.chat.twitch.tv", 6667))
            self.sock.send(f"PASS {self.password}\r\n".encode())
            self.sock.send(f"NICK {self.username}\r\n".encode())
            self.sock.send(f"JOIN #{self.channel}\r\n".encode())
            logger.info(f"Подключено к IRC, канал #{self.channel}")

            buffer = ""
            while self.running:
                try:
                    data = self.sock.recv(4096).decode("utf-8", errors="ignore")
                    if not data:
                        break
                    buffer += data
                    while "\r\n" in buffer:
                        line, buffer = buffer.split("\r\n", 1)
                        try:
                            self._handle_line(line)
                        except Exception as e:
                            logger.error(f"Ошибка обработки строки: {e}")
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Ошибка чтения из сокета: {e}")
                    break
        except Exception as e:
            logger.error(f"Не удалось подключиться к IRC: {e}")
        finally:
            self.running = False
            if self.sock:
                self.sock.close()

    def _handle_line(self, line: str) -> None:
        """Разбирает строку, выделяет сообщение и вызывает callback."""
        if line.startswith("PING"):
            self.sock.send(b"PONG :tmi.twitch.tv\r\n")
            return

        tags = {}
        if line.startswith("@"):
            end_tags = line.find(" ")
            if end_tags != -1:
                tags_part = line[1:end_tags]
                for item in tags_part.split(";"):
                    if "=" in item:
                        key, val = item.split("=", 1)
                        tags[key] = val
                line = line[end_tags + 1:]

        if "PRIVMSG" not in line:
            return

        try:
            parts = line.split(":", 2)
            if len(parts) < 3:
                return
            user_info = parts[1]
            username = user_info.split("!")[0]
            message = parts[2].strip()
        except Exception:
            return

        # Логируем входящее сообщение
        logger.info(f"[{self.channel}] {username}: {message}")

        # Парсим бейджи
        badges_str = tags.get("badges", "")
        badges = []
        if badges_str:
            for b in badges_str.split(","):
                if "/" in b:
                    name, version = b.split("/", 1)
                    badges.append({"name": name, "version": version})

        color = self._generate_color(username)

        message_data = {
            "username": username,
            "message": message,
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "badges": badges,
        }

        if self.on_message:
            try:
                self.on_message(message_data)
            except Exception as e:
                logger.error(f"Ошибка в callback-функции: {e}")

    @staticmethod
    def _generate_color(username: str) -> str:
        """Генерирует цвет на основе хеша имени пользователя."""
        h = hashlib.md5(username.encode()).digest()
        return f"#{h[0]:02x}{h[1]:02x}{h[2]:02x}"