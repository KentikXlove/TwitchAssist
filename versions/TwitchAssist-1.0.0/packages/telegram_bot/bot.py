import requests
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str, proxies: Optional[Dict[str, str]] = None):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.proxies = proxies

    def send_message(self, chat_id: str, text: str) -> bool:
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            # Логируем URL (токен маскируем)
            masked_url = url.replace(self.token, self.token[:6] + '...' + self.token[-4:])
            logger.info(f"Отправка запроса к Telegram: {masked_url}, payload={payload}")

            resp = requests.post(url, json=payload, timeout=10, proxies=self.proxies)
            logger.info(f"Ответ Telegram: статус {resp.status_code}, тело: {resp.text[:200]}")
            if resp.status_code == 200:
                logger.info(f"Telegram сообщение отправлено в чат {chat_id}")
                return True
            else:
                logger.error(f"Ошибка отправки: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Исключение при отправке: {e}")
            return False