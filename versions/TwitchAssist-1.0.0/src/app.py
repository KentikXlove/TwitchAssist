import os
import json
import logging
import multiprocessing
import re
import time
import base64
import io
import threading
from datetime import datetime
from typing import List

try:
    import qrcode
except ImportError:
    qrcode = None

from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO, emit

from packages.twitch_decapi import TwitchClient
from packages.twitch_irc import TwitchIRC
from packages.DataBase import Database, JSONStorage
from packages.web_window.window import run_window
from packages.emote_processor import EmoteProcessor
from packages.chart import ChartCollector
from packages.tts import TTSClient
from packages.telegram_bot import TelegramBot
from packages.proxy_manager import ProxyManager

# Настройка корневого логгера
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Пути ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMOTES_FILE = os.path.join(BASE_DIR, 'src', 'emotes.json')
STYLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'styles')
os.makedirs(STYLES_DIR, exist_ok=True)
ICON_PATH = os.path.join(BASE_DIR, 'icon.ico')
# --- Инициализация обработчика смайликов ---
emote_processor = EmoteProcessor(emotes_file=EMOTES_FILE, log_level=logging.INFO)

# --- Функции для работы со стилями ---
def get_available_styles() -> List[str]:
    if not os.path.exists(STYLES_DIR):
        return []
    files = [f for f in os.listdir(STYLES_DIR) if f.endswith('.css')]
    return sorted(files)

def get_style_content(filename: str) -> str:
    filepath = os.path.join(STYLES_DIR, filename)
    if os.path.exists(filepath) and os.path.isfile(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return ''

# --- Глобальные функции для запуска окон ---
def _run_chat_window():
    run_window('http://127.0.0.1:5001/chat', title='Чат TwitchAssist', width=600, height=700, icon_path=ICON_PATH)

def _run_user_chat_window(username):
    run_window(f'http://127.0.0.1:5001/chat/user/{username}', title=f'Чат - {username}', width=600, height=700, icon_path=ICON_PATH)

# --- Фильтр плохих слов ---
def filter_bad_words(text: str, bad_words: list) -> str:
    if not bad_words:
        return text
    for word in bad_words:
        pattern = r'\b' + re.escape(word) + r'\b'
        text = re.sub(pattern, '*' * len(word), text, flags=re.IGNORECASE)
    return text

# --- Состояние приложения ---
class AppState:
    def __init__(self, config_db: Database, socketio: SocketIO):
        self.config_db = config_db
        self.socketio = socketio
        self._init_default_config()
        self.channel = self._load_channel()
        self.messages_queue = []
        self.message_history = []
        self.max_history = 200
        self.twitch_client = None
        self.irc_client = None
        self._init_clients()

        # Настройка логгирования чата
        self.chat_log_dir = 'chat_logs'
        os.makedirs(self.chat_log_dir, exist_ok=True)
        self.chat_log_file = os.path.join(
            self.chat_log_dir,
            f"chat_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        )
        self.chat_logger = None
        self._setup_chat_logger()

        # --- Сборщики данных для графиков ---
        interval = self.config_db.get('overlay', {}).get('chart_interval', 300)
        self.viewers_collector = ChartCollector(
            get_value_func=lambda: self.twitch_client.get_viewers() if self.twitch_client else 0,
            socketio=self.socketio,
            interval=interval,
            event_name='viewers_chart_update'
        )
        self.viewers_collector.start()

        self.followers_collector = ChartCollector(
            get_value_func=lambda: self.twitch_client.get_followers() if self.twitch_client else 0,
            socketio=self.socketio,
            interval=interval,
            event_name='followers_chart_update'
        )
        self.followers_collector.start()

        # --- TTS клиент ---
        overlay = self.config_db.get('overlay') or {}
        self.tts_client = TTSClient(overlay.get('tts', {}))

        # --- Telegram уведомления ---
        self.telegram_bot = None
        self.telegram_chat_id = None
        self.telegram_notify_enabled = False
        self.telegram_notify_sent = False
        self.last_online = False
        self.monitor_thread = None
        self.monitor_running = False
        self.monitor_interval = self.config_db.get('overlay', {}).get('channel_update_interval', 60)
        self.proxy_manager = None
        self._init_telegram()
        self._start_monitor()

    def _setup_chat_logger(self):
        self.chat_logger = logging.getLogger('chat_logger')
        self.chat_logger.setLevel(logging.INFO)
        if self.chat_logger.handlers:
            self.chat_logger.handlers.clear()
        fh = logging.FileHandler(self.chat_log_file, encoding='utf-8')
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(formatter)
        self.chat_logger.addHandler(fh)

    def _init_default_config(self):
        defaults = {
            'channel': '',
            'overlay': {
                'style': 'dark.css',
                'custom_css': '',
                'show_avatar': True,
                'bad_words': [],
                'log_enabled': True,
                'chart_interval': 300,
                'channel_update_interval': 300,
                'always_on_top': False,
                'message_ttl': 0,
                'tts': {
                    'enabled': False,
                    'mode': 'all_except',
                    'users': [],
                    'speed': 200,
                    'volume': 50,
                    "engine": "edge",
                    "voice": "ru-RU-SvetlanaNeural"
                },
                'overlays': {
                    'chat_enabled': True,
                    'telegram_enabled': False,
                    'telegram_username': '',
                    'telegram_style': 'dark.css',
                    'telegram_custom_css': ''
                },
                'telegram_bot_token': '',
                'telegram_chat_id': '',
                'telegram_notify_enabled': False,
                'proxy_url': '',
                'telegram_notification_template': '🔴 <b>{channel}</b> начал стрим!\n\n📺 <a href="{url}">{title}</a>\n🎮 {game}\n👁 {viewers} зрителей'
            }
        }
        if not self.config_db.exists('channel'):
            self.config_db.set('channel', defaults['channel'])
        if not self.config_db.exists('overlay'):
            self.config_db.set('overlay', defaults['overlay'])
        else:
            overlay = self.config_db.get('overlay')
            for k, v in defaults['overlay'].items():
                if k not in overlay:
                    overlay[k] = v
                if k == 'tts' and isinstance(v, dict):
                    tts = overlay.get('tts', {})
                    for ttk, ttv in v.items():
                        if ttk not in tts:
                            tts[ttk] = ttv
                    overlay['tts'] = tts
                if k == 'overlays' and isinstance(v, dict):
                    ov = overlay.get('overlays', {})
                    for ovk, ovv in v.items():
                        if ovk not in ov:
                            ov[ovk] = ovv
                    overlay['overlays'] = ov
            self.config_db.set('overlay', overlay)

    def _load_channel(self) -> str:
        channel = self.config_db.get('channel')
        return channel if channel else ''

    def _init_clients(self):
        if not self.channel:
            logger.warning("Канал не указан, клиенты не инициализированы")
            self.twitch_client = None
            if self.irc_client:
                self.irc_client.stop()
                self.irc_client = None
            return

        self.twitch_client = TwitchClient(self.channel)
        if self.irc_client:
            self.irc_client.stop()
        self.irc_client = TwitchIRC(
            on_message=self._on_irc_message
        )
        self.irc_client.start(self.channel)
        logger.info(f"Клиенты инициализированы для канала {self.channel}")

    def _on_irc_message(self, msg):
        raw_text = msg['message']
        overlay_settings = self.config_db.get('overlay') or {}
        bad_words = overlay_settings.get('bad_words', [])
        filtered_text = filter_bad_words(raw_text, bad_words)

        processed_text, detected = emote_processor.process_message(
            username=msg['username'],
            message=filtered_text
        )
        msg['processed_text'] = processed_text
        msg['detected_emotes'] = detected
        msg['original_text'] = raw_text

        if overlay_settings.get('log_enabled', True):
            self._log_message(msg)

        self.message_history.append(msg)
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]
        self.messages_queue.append(msg)

        # TTS
        self.tts_client.process_message(msg)

    def _log_message(self, msg):
        if self.chat_logger:
            self.chat_logger.info(f"{msg['username']}: {msg['original_text']}")

    def update_channel(self, new_channel: str):
        if new_channel == self.channel:
            return
        self.viewers_collector.clear()
        self.viewers_collector.stop()
        self.followers_collector.clear()
        self.followers_collector.stop()
        self.channel = new_channel
        self.config_db.set('channel', new_channel)
        self.message_history.clear()
        self.messages_queue.clear()
        self._init_clients()
        if not self.channel:
            return
        interval = self.config_db.get('overlay', {}).get('chart_interval', 300)
        self.viewers_collector = ChartCollector(
            get_value_func=lambda: self.twitch_client.get_viewers() if self.twitch_client else 0,
            socketio=self.socketio,
            interval=interval,
            event_name='viewers_chart_update'
        )
        self.viewers_collector.start()
        self.followers_collector = ChartCollector(
            get_value_func=lambda: self.twitch_client.get_followers() if self.twitch_client else 0,
            socketio=self.socketio,
            interval=interval,
            event_name='followers_chart_update'
        )
        self.followers_collector.start()
        self.tts_client.clear_queue()
        self.last_online = False
        self.telegram_notify_sent = False
        self._stop_monitor()
        self._start_monitor()
        logger.info(f"Канал изменён на {self.channel}")

    def update_overlay_settings(self, new_settings: dict):
        current = self.config_db.get('overlay') or {}
        current.update(new_settings)
        self.config_db.set('overlay', current)
        if 'chart_interval' in new_settings:
            self.viewers_collector.set_interval(new_settings['chart_interval'])
            self.followers_collector.set_interval(new_settings['chart_interval'])
        self.tts_client.update_config(current.get('tts', {}))
        self.socketio.emit('overlay_settings_updated', current.get('overlays', {}))

        if any(k in new_settings for k in ('telegram_bot_token', 'telegram_chat_id', 'telegram_notify_enabled', 'proxy_url')):
            self._init_telegram()
            self._start_monitor()
        if 'channel_update_interval' in new_settings:
            self.monitor_interval = new_settings['channel_update_interval']
            self._stop_monitor()
            self._start_monitor()

        logger.info(f"Настройки оверлея обновлены: {new_settings}")

    def get_recent_messages(self, limit=50):
        return self.message_history[-limit:]

    def get_overlay_css(self) -> str:
        settings = self.config_db.get('overlay') or {}
        style = settings.get('style', 'dark.css')
        custom_css = settings.get('custom_css', '')

        if style == 'custom' and custom_css:
            return custom_css

        if style and style.endswith('.css'):
            content = get_style_content(style)
            if content:
                return content

        return get_style_content('dark.css') or '/* базовый стиль не найден */'

    def get_overlay_settings(self) -> dict:
        return self.config_db.get('overlay', {}).get('overlays', {})

    # ---------- Telegram уведомления ----------
    def _init_telegram(self):
        overlay = self.config_db.get('overlay') or {}
        token = overlay.get('telegram_bot_token', '')
        chat_id = overlay.get('telegram_chat_id', '')
        enabled = overlay.get('telegram_notify_enabled', False)
        proxy_url = overlay.get('proxy_url', '')

        # Логируем загруженные значения (токен маскируем)
        masked_token = token[:6] + '...' + token[-4:] if len(token) > 10 else '(пусто)'
        logger.info(
            f"Загрузка настроек Telegram: enabled={enabled}, chat_id={chat_id}, token={masked_token}, proxy={proxy_url or 'нет'}")

        self.telegram_notify_enabled = enabled
        self.telegram_chat_id = chat_id
        self.proxy_manager = ProxyManager(proxy_url)
        proxies = self.proxy_manager.get_proxies()

        if token and chat_id:
            self.telegram_bot = TelegramBot(token, proxies=proxies)
            logger.info("Telegram бот успешно инициализирован" + (f" с прокси {proxy_url}" if proxy_url else ""))
        else:
            self.telegram_bot = None
            if not token:
                logger.warning("Токен бота не задан")
            elif not chat_id:
                logger.warning("ID чата не задан")

    def _start_monitor(self):
        self._stop_monitor()
        if not self.channel:
            return
        if not self.telegram_notify_enabled or not self.telegram_bot:
            return
        self.monitor_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Мониторинг статуса стрима запущен")

    def _stop_monitor(self):
        self.monitor_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)
        self.monitor_thread = None

    def _monitor_loop(self):
        while self.monitor_running:
            try:
                if not self.twitch_client:
                    time.sleep(self.monitor_interval)
                    continue
                viewers = self.twitch_client.get_viewers() or 0
                online = viewers > 0

                if online and not self.last_online and not self.telegram_notify_sent:
                    if self._send_stream_notification():
                        self.telegram_notify_sent = True
                elif not online:
                    self.telegram_notify_sent = False

                self.last_online = online
                time.sleep(self.monitor_interval)
            except Exception as e:
                logger.error(f"Ошибка в мониторинге стрима: {e}")
                time.sleep(self.monitor_interval)

    def _send_stream_notification(self) -> bool:
        """Отправка уведомления с использованием шаблона"""
        if not self.telegram_bot or not self.telegram_chat_id:
            return False
        overlay = self.config_db.get('overlay') or {}
        template = overlay.get('telegram_notification_template', '')
        if not template:
            # шаблон по умолчанию
            template = "🔴 <b>{channel}</b> начал стрим!\n\n📺 <a href=\"{url}\">{title}</a>\n🎮 {game}\n👁 {viewers} зрителей"
        # Получаем данные
        channel = self.channel
        title = self.twitch_client.get_title() if self.twitch_client else ''
        game = self.twitch_client.get_game() if self.twitch_client else ''
        viewers = self.twitch_client.get_viewers() or 0
        url = f"https://twitch.tv/{channel}"
        # Заменяем переменные
        text = template.format(channel=channel, title=title, game=game, viewers=viewers, url=url)
        return self.telegram_bot.send_message(self.telegram_chat_id, text)

    def send_manual_notification(self) -> bool:
        """Ручная отправка уведомления (вызывается по кнопке)"""
        return self._send_stream_notification()

# --- Создание Flask-приложения ---
def create_app():
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.config['SECRET_KEY'] = 'secret!'
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

    config_storage = JSONStorage('config.json')
    config_db = Database(config_storage, default_ttl=None)
    state = AppState(config_db, socketio)

    # --- WebSocket обработчики ---
    @socketio.on('connect')
    def handle_connect():
        logger.info('Клиент подключился к WebSocket')
        recent = state.get_recent_messages(limit=50)
        emit('chat_history', recent)
        emit('viewers_chart_history', state.viewers_collector.get_data())
        emit('followers_chart_history', state.followers_collector.get_data())
        emit('overlay_settings_updated', state.get_overlay_settings())

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info('Клиент отключился от WebSocket')

    # --- HTTP маршруты ---
    @app.route('/')
    def index():
        return render_template('index.html', channel=state.channel)

    @app.route('/chat', methods=['GET', 'POST'])
    def chat():
        if request.method == 'POST':
            ctx = multiprocessing.get_context('spawn')
            p = ctx.Process(target=_run_chat_window)
            p.start()
            return jsonify({'status': 'window opened'}), 200
        return render_template('chat_only.html', channel=state.channel, filter_user=None)

    @app.route('/chat/user/<username>', methods=['GET', 'POST'])
    def chat_user(username):
        if request.method == 'POST':
            ctx = multiprocessing.get_context('spawn')
            p = ctx.Process(target=_run_user_chat_window, args=(username,))
            p.start()
            return jsonify({'status': 'window opened'}), 200
        return render_template('chat_only.html', channel=state.channel, filter_user=username)

    @app.route('/overlay')
    def overlay():
        return render_template('overlay.html')

    @app.route('/overlay/telegram')
    def overlay_telegram():
        settings = state.get_overlay_settings()
        username = settings.get('telegram_username', '')
        style_name = settings.get('telegram_style', 'dark.css')
        custom_css = settings.get('telegram_custom_css', '')
        qr_base64 = None
        if username and qrcode is not None:
            try:
                qr = qrcode.QRCode(box_size=10, border=4)
                qr.add_data(f"https://t.me/{username}")
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            except Exception as e:
                logger.error(f"Ошибка генерации QR: {e}")
        return render_template('overlay_telegram.html',
                               username=username,
                               qr_base64=qr_base64,
                               style_name=style_name,
                               custom_css=custom_css)

    @app.route('/api/qr')
    def generate_qr():
        username = request.args.get('username', '')
        if not username:
            return jsonify({'error': 'Username required'}), 400
        if qrcode is None:
            return jsonify({'error': 'qrcode library not installed'}), 500
        try:
            qr = qrcode.QRCode(box_size=10, border=4)
            qr.add_data(f"https://t.me/{username}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return send_file(buf, mimetype='image/png')
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/avatar/<username>')
    def get_avatar(username):
        try:
            import requests
            url = f"https://decapi.me/twitch/avatar/{username}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return jsonify({'url': resp.text.strip()})
            else:
                return jsonify({'error': 'avatar not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/channel')
    def channel_info():
        try:
            if state.twitch_client is None:
                # Если клиент не инициализирован, возвращаем пустые данные
                return jsonify({
                    'channel': state.channel or '',
                    'viewers': 0,
                    'followers': 0,
                    'game': '—',
                    'title': '—',
                    'uptime': 'Offline',
                    'avatar_url': ''
                })
            data = state.twitch_client.get_all()
            data['channel'] = state.channel
            return jsonify(data)
        except Exception as e:
            logger.error(f"Ошибка получения данных: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/emotes')
    def get_emotes():
        return jsonify(emote_processor.get_emotes())

    @app.route('/api/styles')
    def api_styles():
        return jsonify(get_available_styles())

    @app.route('/api/style')
    def api_style():
        name = request.args.get('name', '')
        if not name:
            return jsonify({'error': 'Missing name parameter'}), 400
        content = get_style_content(name)
        if not content:
            return jsonify({'error': 'Style not found'}), 404
        return jsonify({'name': name, 'content': content})

    @app.route('/api/viewers_chart')
    def viewers_chart_data():
        return jsonify(state.viewers_collector.get_data())

    @app.route('/api/followers_chart')
    def followers_chart_data():
        return jsonify(state.followers_collector.get_data())

    @app.route('/api/config', methods=['GET', 'POST'])
    def config():
        if request.method == 'GET':
            return jsonify({
                'channel': state.channel,
                'overlay': state.config_db.get('overlay')
            })
        data = request.get_json()
        new_channel = data.get('channel', '').strip()
        if new_channel and new_channel != state.channel:
            state.update_channel(new_channel)
            socketio.emit('channel_changed', {'channel': new_channel})

        overlay = data.get('overlay')
        if overlay:
            current_overlay = state.config_db.get('overlay') or {}
            for key in overlay:
                current_overlay[key] = overlay[key]
            state.config_db.set('overlay', current_overlay)
            state.update_overlay_settings(current_overlay)
            socketio.emit('settings_updated', {'overlay': current_overlay})

        return jsonify({'channel': state.channel, 'status': 'updated'})

    @app.route('/api/tts/voices')
    def tts_voices():
        engine = request.args.get('engine', 'pyttsx3')
        voices = TTSClient.get_voices(engine)
        return jsonify(voices)

    @app.route('/api/test_telegram', methods=['POST'])
    def test_telegram():
        logger.info(f"telegram_bot: {state.telegram_bot}, chat_id: {state.telegram_chat_id}")
        if not state.telegram_bot:
            return jsonify(
                {'success': False, 'error': 'Бот не инициализирован. Проверьте токен и ID чата.'}), 400
        if not state.telegram_chat_id:
            return jsonify({'success': False, 'error': 'ID чата не задан'}), 400
        success = state.telegram_bot.send_message(
            state.telegram_chat_id,
            "✅ Тестовое сообщение из TwitchAssist"
        )
        return jsonify({'success': success})

    @app.route('/api/test_proxy', methods=['POST'])
    def test_proxy():
        data = request.get_json()
        proxy_url = data.get('proxy_url', '').strip()
        if not proxy_url:
            return jsonify({'success': False, 'error': 'Прокси не указан'}), 400

        proxy_manager = ProxyManager(proxy_url)
        proxies = proxy_manager.get_proxies()
        if not proxies:
            return jsonify({'success': False, 'error': 'Неверный формат прокси'}), 400

        try:
            import requests
            test_url = 'https://api.telegram.org/bot' + state.config_db.get('overlay', {}).get('telegram_bot_token', '') + '/getMe'
            if not state.config_db.get('overlay', {}).get('telegram_bot_token'):
                resp = requests.get('https://api.telegram.org', proxies=proxies, timeout=10)
                if resp.status_code == 200:
                    return jsonify({'success': True, 'message': 'Прокси работает (подключение к api.telegram.org установлено)'})
                else:
                    return jsonify({'success': False, 'error': f'Прокси не отвечает (код {resp.status_code})'}), 400
            else:
                resp = requests.get(test_url, proxies=proxies, timeout=10)
                if resp.status_code == 200:
                    return jsonify({'success': True, 'message': 'Прокси работает, бот доступен'})
                else:
                    return jsonify({'success': False, 'error': f'Ошибка при запросе через прокси (код {resp.status_code}): {resp.text}'}), 400
        except requests.exceptions.ProxyError as e:
            return jsonify({'success': False, 'error': f'Ошибка прокси: {str(e)}'}), 400
        except requests.exceptions.Timeout:
            return jsonify({'success': False, 'error': 'Таймаут при подключении через прокси'}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': f'Ошибка: {str(e)}'}), 400

    # ---- НОВЫЙ ЭНДПОЙНТ ДЛЯ РУЧНОЙ ОТПРАВКИ УВЕДОМЛЕНИЯ ----
    @app.route('/api/send_telegram_notification', methods=['POST'])
    def send_telegram_notification():
        if not state.telegram_bot:
            return jsonify({'success': False, 'error': 'Бот не инициализирован. Проверьте токен и ID чата.'}), 400
        if not state.telegram_chat_id:
            return jsonify({'success': False, 'error': 'ID чата не задан'}), 400
        if not state.channel:
            return jsonify({'success': False, 'error': 'Канал не задан'}), 400
        try:
            success = state.send_manual_notification()
            if success:
                return jsonify({'success': True, 'message': 'Уведомление отправлено'})
            else:
                return jsonify({'success': False, 'error': 'Ошибка при отправке сообщения'}), 500
        except Exception as e:
            logger.error(f"Ошибка при ручной отправке уведомления: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # --- Фоновый поток для отправки новых сообщений ---
    def send_messages():
        while True:
            if state.messages_queue:
                msg = state.messages_queue.pop(0)
                socketio.emit('new_message', msg)
            else:
                time.sleep(0.3)

    socketio.start_background_task(target=send_messages)

    return app, socketio