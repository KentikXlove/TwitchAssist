import threading
import queue
import logging
import time
import asyncio
import tempfile
import os
from typing import Dict, Any, List, Optional
import re
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    import pygame
except ImportError:
    pygame = None

from .exceptions import TTSException

logger = logging.getLogger(__name__)

class TTSClient:
    def __init__(self, initial_config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = initial_config.copy()
        self.queue = queue.Queue()
        self.running = False
        self.thread = None
        self.pytts_engine = None
        self.pygame_initialized = False
        self._init_engine()
        self._start_worker()

    def _init_engine(self):
        engine = self.config.get('engine', 'pyttsx3')
        if engine == 'pyttsx3' and pyttsx3 is not None:
            if self.pytts_engine is None:
                try:
                    self.pytts_engine = pyttsx3.init()
                except Exception as e:
                    self.logger.error(f"Ошибка инициализации pyttsx3: {e}")
        elif engine == 'pyttsx3' and pyttsx3 is None:
            self.logger.warning("pyttsx3 не установлен, переключение на edge")
            self.config['engine'] = 'edge'

    def _start_worker(self):
        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _remove_urls(self, text: str) -> str:
        """Заменяет все URL-адреса в тексте на слово 'ссылка'."""
        # Простое регулярное выражение для обнаружения http/https/ftp ссылок
        url_pattern = r'https?://\S+|www\.\S+'
        return re.sub(url_pattern, 'ссылка', text)

    def _worker(self):
        while self.running:
            try:
                first_msg = self.queue.get(timeout=0.5)
                if first_msg is None:
                    break
                username = first_msg['username']
                texts = [first_msg['text']]

                # Собираем все следующие сообщения от того же пользователя
                while True:
                    try:
                        next_msg = self.queue.get_nowait()
                        if next_msg is None:
                            break
                        if next_msg['username'] == username:
                            texts.append(next_msg['text'])
                        else:
                            self.queue.put(next_msg)
                            break
                    except queue.Empty:
                        break

                combined = ', '.join(texts) if len(texts) > 1 else texts[0]
                # Очищаем текст от ссылок перед озвучиванием
                cleaned = self._remove_urls(combined)
                self._speak(f"{username} сказал {cleaned}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Ошибка в TTS воркере: {e}")

    def _speak(self, text: str):
        engine = self.config.get('engine', 'pyttsx3')
        if engine == 'pyttsx3':
            self._speak_pyttsx3(text)
        elif engine == 'edge':
            self._speak_edge(text)
        else:
            self.logger.warning(f"Неизвестный движок TTS: {engine}")

    def _speak_pyttsx3(self, text: str):
        if self.pytts_engine is None:
            try:
                self.pytts_engine = pyttsx3.init()
            except Exception as e:
                self.logger.error(f"Не удалось инициализировать pyttsx3: {e}")
                return
        speed = self.config.get('speed', 200)
        volume = self.config.get('volume', 50) / 100.0
        voice_id = self.config.get('voice')
        self.pytts_engine.setProperty('rate', speed)
        self.pytts_engine.setProperty('volume', max(0.0, min(1.0, volume)))
        if voice_id:
            try:
                self.pytts_engine.setProperty('voice', voice_id)
            except:
                pass
        self.pytts_engine.say(text)
        self.pytts_engine.runAndWait()

    def _speak_edge(self, text: str):
        if edge_tts is None:
            self.logger.error("edge-tts не установлен")
            return
        voice = self.config.get('voice', 'en-US-JennyNeural')
        speed = self.config.get('speed', 200)
        percent = (speed - 200) / 200 * 100
        rate_str = f"{'+' if percent >= 0 else ''}{percent:.0f}%"
        volume = self.config.get('volume', 50) / 100.0

        async def generate():
            communicate = edge_tts.Communicate(text, voice, rate=rate_str)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
                await communicate.save(tmp.name)
                return tmp.name

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_file = loop.run_until_complete(generate())
            loop.close()
        except Exception as e:
            self.logger.error(f"Ошибка генерации аудио через edge-tts: {e}")
            return

        if pygame is None:
            self.logger.error("pygame не установлен, невозможно воспроизвести аудио")
            try:
                os.unlink(audio_file)
            except:
                pass
            return
        try:
            if not self.pygame_initialized:
                pygame.mixer.init()
                self.pygame_initialized = True
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.music.unload()
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения аудио: {e}")
        finally:
            try:
                os.unlink(audio_file)
            except:
                pass

    def process_message(self, msg: Dict[str, Any]):
        if not self.config.get('enabled', False):
            return
        username = msg.get('username', '')
        text = msg.get('message', '')
        if not text:
            return
        mode = self.config.get('mode', 'all_except')
        users_raw = self.config.get('users', [])
        if isinstance(users_raw, str):
            users = [u.strip().lower() for u in users_raw.split(',') if u.strip()]
        else:
            users = [u.lower() for u in users_raw if u]
        if mode == 'all_except':
            if username.lower() in users:
                return
        elif mode == 'only':
            if username.lower() not in users:
                return
        self.queue.put({'username': username, 'text': text})

    def update_config(self, new_config: Dict[str, Any]):
        old_enabled = self.config.get('enabled', False)
        new_enabled = new_config.get('enabled', False)
        old_engine = self.config.get('engine')
        new_engine = new_config.get('engine', 'pyttsx3')
        self.config.update(new_config)

        if old_enabled and not new_enabled:
            self.clear_queue()

        if old_engine != new_engine:
            if self.pytts_engine:
                try:
                    self.pytts_engine.stop()
                except:
                    pass
                self.pytts_engine = None
            if new_engine == 'pyttsx3' and pyttsx3 is not None:
                try:
                    self.pytts_engine = pyttsx3.init()
                except Exception as e:
                    self.logger.error(f"Ошибка инициализации pyttsx3: {e}")

    def clear_queue(self):
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
        self.logger.info("Очередь TTS очищена")

    def stop(self):
        self.running = False
        self.clear_queue()
        self.queue.put(None)
        if self.thread:
            self.thread.join(timeout=1)
        if self.pytts_engine:
            try:
                self.pytts_engine.stop()
            except:
                pass
        if self.pygame_initialized:
            try:
                pygame.mixer.quit()
            except:
                pass
            self.pygame_initialized = False

    @staticmethod
    def get_voices(engine: str) -> List[Dict[str, str]]:
        if engine == 'pyttsx3':
            if pyttsx3 is None:
                return []
            try:
                eng = pyttsx3.init()
                voices = eng.getProperty('voices')
                result = []
                for v in voices:
                    lang = v.languages[0] if v.languages else ''
                    result.append({'id': v.id, 'name': v.name, 'lang': lang})
                eng.stop()
                return result
            except Exception as e:
                logger.error(f"Ошибка получения голосов pyttsx3: {e}")
                return []
        elif engine == 'edge':
            if edge_tts is None:
                return []
            try:
                voices = asyncio.run(edge_tts.list_voices())
                result = []
                for v in voices:
                    result.append({
                        'id': v['ShortName'],
                        'name': v.get('Name', v['ShortName']),
                        'lang': v.get('Locale', '')
                    })
                return result
            except Exception as e:
                logger.error(f"Ошибка получения голосов edge: {e}")
                return []
        else:
            return []