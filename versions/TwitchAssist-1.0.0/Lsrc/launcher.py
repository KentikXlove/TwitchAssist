import os
import sys
import json
import zipfile
import requests
import time
import logging
import re
import shutil
import threading
import webbrowser
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.serving import make_server

# Импортируем run_window для открытия встроенного браузера
from packages.web_window.window import run_window

# ---------- Настройка логирования ----------
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('launcher_debug.log', encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ---------- Константы ----------
VERSIONS_URL = "https://cdn.jsdelivr.net/gh/KentikXlove/TwitchAssist@main/versions.json"
STORE_URL = "https://raw.githubusercontent.com/KentikXlove/TwitchAssist/main/additional_content.json"
INSTALL_BASE_PATH = "C:/TwitchAssist"

# ---------- Глобальное состояние ----------
state = {
    "status": "ready",
    "status_text": "Готов к работе",
    "progress": 0,
    "downloads": [],
    "current_app_process": None,
}

# ---------- Вспомогательные функции ----------
def safe_remove(path):
    for _ in range(5):
        try:
            if os.path.exists(path):
                os.remove(path)
            return
        except:
            time.sleep(0.5)

def download_file(source, dest, is_direct=False, name="Файл", progress_callback=None):
    session = requests.Session()
    try:
        logger.info(f"Загрузка из источника: {source}")
        if is_direct:
            response = session.get(source, stream=True)
        else:
            url = "https://drive.google.com/uc"
            params = {'id': source, 'export': 'download'}
            response = session.get(url, params=params)
            if 'uc-download-link' in response.text or 'confirm' in response.text:
                form_data = {}
                for name_val, value in re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]+)"', response.text):
                    form_data[name_val] = value
                action = re.search(r'<form[^>]+action="([^"]+)"', response.text)
                action_url = action.group(1) if action else "https://drive.usercontent.google.com/download"
                for k, v in params.items():
                    if k not in form_data:
                        form_data[k] = v
                download_response = session.get(action_url, params=form_data, stream=True)
                if download_response.history:
                    final = download_response.history[-1]
                    if final.status_code == 302 and final.headers.get('Location'):
                        download_response = session.get(final.headers['Location'], stream=True)
                response = download_response
            else:
                response = session.get(f"https://drive.google.com/uc?export=download&id={source}", stream=True)

        if response.status_code != 200:
            raise Exception(f"Ошибка скачивания: {response.status_code}")

        total = int(response.headers.get('content-length', 0))
        with open(dest, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=32768):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0 and progress_callback:
                        progress = int(downloaded / total * 100)
                        progress_callback(progress)

        if not os.path.exists(dest) or os.path.getsize(dest) == 0:
            raise Exception("Файл пуст или не создан")
        with open(dest, 'rb') as f:
            head = f.read(200)
            if b'<!DOCTYPE' in head or b'<html' in head:
                safe_remove(dest)
                raise Exception("Сервер вернул HTML")
        return True
    except Exception as e:
        logger.error(f"Ошибка загрузки: {e}", exc_info=True)
        raise

def get_versions_data():
    try:
        resp = requests.get(VERSIONS_URL, timeout=10)
        return resp.json()
    except Exception as e:
        logger.error(f"Ошибка загрузки версий: {e}")
        return {"versions": []}

def get_installed_versions():
    installed = []
    try:
        if not os.path.exists(INSTALL_BASE_PATH):
            return []
        for item in os.listdir(INSTALL_BASE_PATH):
            path = os.path.join(INSTALL_BASE_PATH, item)
            if os.path.isdir(path) and item.startswith('v'):
                version = item[1:]
                exe_name = f"TwitchAssist-{version}.exe"
                exe_path = os.path.join(path, exe_name)
                if os.path.exists(exe_path):
                    installed.append(version)
    except Exception as e:
        logger.error(f"Ошибка получения установленных версий: {e}", exc_info=True)
    return installed

def get_store_items():
    try:
        resp = requests.get(STORE_URL, timeout=10)
        return resp.json().get('items', [])
    except Exception as e:
        logger.error(f"Ошибка загрузки магазина: {e}")
        return []

def get_version_details(version, versions_data):
    if not versions_data:
        return {}
    ver_info = next((v for v in versions_data.get('versions', []) if v['version'] == version), None)
    if not ver_info:
        return {}
    return {
        'version': ver_info.get('version'),
        'release_date': ver_info.get('release_date', 'Неизвестно'),
        'size': ver_info.get('size', 0),
        'is_beta': ver_info.get('is_beta', False),
        'is_stable': ver_info.get('is_stable', True),
        'changelog': ver_info.get('changelog', []),
        'executable': ver_info.get('executable', f"TwitchAssist-{version}.exe")
    }

# ---------- Фоновые задачи ----------
def install_version_task(version, versions_data):
    def progress_callback(percent):
        state["progress"] = percent
        for d in state["downloads"]:
            if d["name"] == f"Версия {version}":
                d["progress"] = percent
                if percent >= 100:
                    d["status"] = "completed"
                break
    try:
        ver_info = next((v for v in versions_data.get('versions', []) if v['version'] == version), None)
        if not ver_info:
            raise Exception(f"Версия {version} не найдена")
        version_path = os.path.join(INSTALL_BASE_PATH, f"v{version}")
        os.makedirs(version_path, exist_ok=True)
        zip_path = os.path.join(version_path, "temp.zip")
        safe_remove(zip_path)

        state["status"] = "downloading"
        state["status_text"] = f"Скачивание версии {version}..."
        state["downloads"].append({"name": f"Версия {version}", "progress": 0, "status": "active"})

        download_file(ver_info['id'], zip_path, is_direct=False, name=f"Версия {version}", progress_callback=progress_callback)

        state["status_text"] = "Распаковка..."
        temp = os.path.join(version_path, "temp_extract")
        os.makedirs(temp, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(temp)
        for item in os.listdir(temp):
            src = os.path.join(temp, item)
            dst = os.path.join(version_path, item)
            if os.path.exists(dst):
                shutil.rmtree(dst) if os.path.isdir(dst) else os.remove(dst)
            shutil.move(src, dst)
        shutil.rmtree(temp)
        safe_remove(zip_path)

        exe_files = [f for f in os.listdir(version_path) if f.endswith('.exe')]
        if exe_files:
            old_exe = os.path.join(version_path, exe_files[0])
            new_exe = os.path.join(version_path, f"TwitchAssist-{version}.exe")
            if old_exe != new_exe:
                os.rename(old_exe, new_exe)
        with open(os.path.join(version_path, "version.txt"), 'w') as f:
            f.write(version)

        state["status"] = "ready"
        state["status_text"] = "Готово"
        state["progress"] = 0
        state["downloads"] = [d for d in state["downloads"] if d["name"] != f"Версия {version}"]
        logger.info(f"Версия {version} установлена успешно")

    except Exception as e:
        logger.error(f"Ошибка установки версии {version}: {e}", exc_info=True)
        state["status"] = "error"
        state["status_text"] = f"Ошибка: {str(e)}"
        state["progress"] = 0
        state["downloads"] = [d for d in state["downloads"] if d["name"] != f"Версия {version}"]

def install_store_item_task(name, download_url, install_path):
    def progress_callback(percent):
        state["progress"] = percent
        for d in state["downloads"]:
            if d["name"] == name:
                d["progress"] = percent
                if percent >= 100:
                    d["status"] = "completed"
                break
    try:
        temp_dir = os.path.join(os.path.dirname(install_path), "temp_download")
        os.makedirs(temp_dir, exist_ok=True)
        zip_path = os.path.join(temp_dir, "temp_file")
        safe_remove(zip_path)

        state["status"] = "downloading"
        state["status_text"] = f"Скачивание {name}..."
        state["downloads"].append({"name": name, "progress": 0, "status": "active"})

        download_file(download_url, zip_path, is_direct=True, name=name, progress_callback=progress_callback)

        state["status_text"] = "Установка..."
        if zipfile.is_zipfile(zip_path):
            os.makedirs(install_path, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(install_path)
        else:
            os.makedirs(os.path.dirname(install_path), exist_ok=True)
            shutil.move(zip_path, install_path)

        safe_remove(zip_path)
        state["status"] = "ready"
        state["status_text"] = "Готово"
        state["progress"] = 0
        state["downloads"] = [d for d in state["downloads"] if d["name"] != name]
        logger.info(f"Товар {name} установлен успешно")

    except Exception as e:
        logger.error(f"Ошибка установки товара {name}: {e}", exc_info=True)
        state["status"] = "error"
        state["status_text"] = f"Ошибка: {str(e)}"
        state["progress"] = 0
        state["downloads"] = [d for d in state["downloads"] if d["name"] != name]

# ---------- Flask приложение ----------
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

versions_cache = None

@app.route('/')
def index():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/versions')
def api_versions():
    global versions_cache
    if versions_cache is None:
        versions_cache = get_versions_data()
    return jsonify(versions_cache)

@app.route('/api/installed')
def api_installed():
    return jsonify(get_installed_versions())

@app.route('/api/version_details/<version>')
def api_version_details(version):
    global versions_cache
    if versions_cache is None:
        versions_cache = get_versions_data()
    details = get_version_details(version, versions_cache)
    return jsonify(details)

@app.route('/api/install_version', methods=['POST'])
def api_install_version():
    data = request.get_json()
    version = data.get('version')
    if not version:
        return jsonify({"error": "Version not specified"}), 400
    if state["status"] == "downloading":
        return jsonify({"error": "Already downloading"}), 400
    if state.get("current_app_process") and state["current_app_process"].poll() is None:
        return jsonify({"error": "Приложение запущено. Закройте его."}), 400
    global versions_cache
    if versions_cache is None:
        versions_cache = get_versions_data()
    thread = threading.Thread(target=install_version_task, args=(version, versions_cache), daemon=True)
    thread.start()
    return jsonify({"status": "started"})

@app.route('/api/uninstall_version', methods=['POST'])
def api_uninstall_version():
    data = request.get_json()
    version = data.get('version')
    if not version:
        return jsonify({"error": "Version not specified"}), 400
    if state.get("current_app_process") and state["current_app_process"].poll() is None:
        return jsonify({"error": "Приложение запущено. Закройте его."}), 400
    version_path = os.path.join(INSTALL_BASE_PATH, f"v{version}")
    if not os.path.exists(version_path):
        return jsonify({"error": "Версия не установлена"}), 404
    try:
        shutil.rmtree(version_path)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/start_app', methods=['POST'])
def api_start_app():
    data = request.get_json()
    version = data.get('version')
    if not version:
        return jsonify({"error": "Version not specified"}), 400
    version_path = os.path.join(INSTALL_BASE_PATH, f"v{version}")
    details = get_version_details(version, versions_cache or {})
    exe_name = details.get('executable', f"TwitchAssist-{version}.exe")
    app_path = os.path.join(version_path, exe_name)
    if not os.path.exists(app_path):
        return jsonify({"error": "Версия не установлена"}), 404
    try:
        import subprocess
        proc = subprocess.Popen([app_path], cwd=version_path)
        state["current_app_process"] = proc
        state["status"] = "running"
        state["status_text"] = f"Запущена версия {version}"
        def monitor():
            proc.wait()
            state["current_app_process"] = None
            state["status"] = "ready"
            state["status_text"] = "Готово"
        threading.Thread(target=monitor, daemon=True).start()
        return jsonify({"status": "started"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/open_folder', methods=['POST'])
def api_open_folder():
    data = request.get_json()
    version = data.get('version')
    if not version:
        return jsonify({"error": "Version not specified"}), 400
    version_path = os.path.join(INSTALL_BASE_PATH, f"v{version}")
    if not os.path.exists(version_path):
        return jsonify({"error": "Папка не найдена"}), 404
    try:
        if sys.platform == 'win32':
            os.startfile(version_path)
        else:
            webbrowser.open('file://' + version_path)
        return jsonify({"status": "opened"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/store')
def api_store():
    items = get_store_items()
    return jsonify(items)
# Вспомогательная функция для проверки, установлен ли товар
def is_store_item_installed(item):
    install_path = item.get('install_path', '')
    if not install_path:
        return False
    # Проверяем наличие папки или файла
    if os.path.exists(install_path):
        # Если это папка – проверяем, не пуста ли она
        if os.path.isdir(install_path):
            if os.listdir(install_path):
                return True
        else:
            return True
    return False

# Эндпоинт для получения статуса установки товаров
@app.route('/api/store_installed', methods=['POST'])
def api_store_installed():
    data = request.get_json()
    items = data.get('items', [])
    result = []
    for item in items:
        result.append({
            'name': item.get('name'),
            'installed': is_store_item_installed(item)
        })
    return jsonify(result)

# Эндпоинт для удаления товара
@app.route('/api/uninstall_store', methods=['POST'])
def api_uninstall_store():
    data = request.get_json()
    install_path = data.get('install_path')
    if not install_path:
        return jsonify({"error": "Missing install_path"}), 400
    if not os.path.exists(install_path):
        return jsonify({"error": "Товар не установлен"}), 404
    try:
        if os.path.isdir(install_path):
            shutil.rmtree(install_path)
        else:
            os.remove(install_path)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/install_store', methods=['POST'])
def api_install_store():
    data = request.get_json()
    name = data.get('name')
    download_url = data.get('download_url')
    install_path = data.get('install_path')
    if not all([name, download_url, install_path]):
        return jsonify({"error": "Missing parameters"}), 400
    if state["status"] == "downloading":
        return jsonify({"error": "Already downloading"}), 400
    if state.get("current_app_process") and state["current_app_process"].poll() is None:
        return jsonify({"error": "Приложение запущено. Закройте его."}), 400
    thread = threading.Thread(target=install_store_item_task, args=(name, download_url, install_path), daemon=True)
    thread.start()
    return jsonify({"status": "started"})

@app.route('/api/status')
def api_status():
    return jsonify({
        "status": state["status"],
        "status_text": state["status_text"],
        "progress": state["progress"],
        "downloads": state["downloads"]
    })

# ---------- Запуск ----------
def run_flask(port):
    server = make_server('127.0.0.1', port, app)
    server.serve_forever()

if __name__ == '__main__':
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()

    flask_thread = threading.Thread(target=run_flask, args=(port,), daemon=True)
    flask_thread.start()
    time.sleep(1)

    url = f"http://127.0.0.1:{port}"
    logger.info(f"Запуск веб-интерфейса на {url}")
    try:
        run_window(url, title="TwitchAssist Launcher", width=1200, height=850, always_on_top=False)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Закрытие приложения")
        sys.exit(0)