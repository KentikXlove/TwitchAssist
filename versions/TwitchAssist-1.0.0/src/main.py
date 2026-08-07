import sys
import os
import threading
import json
import urllib.request   # добавлен для скачивания

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages'))

from app import create_app
from packages.web_window.window import run_window

def main():
    # ---------------------- Проверка критических файлов ----------------------
    # Определяем корневую директорию проекта (там же, где лежит этот скрипт)
    root_dir = os.path.dirname(os.path.abspath(__file__))

    # Список критических файлов: каждый элемент – словарь с путём (относительно root_dir) и URL для скачивания
    critical_files = [
        {
            'path': 'emotes.json',
            'url': 'https://raw.githubusercontent.com/KentikXlove/TwitchAssist/main/emotes.json'
        }
        # При необходимости можно добавить другие файлы, например:
        # {'path': 'another_file.txt', 'url': 'https://example.com/file.txt'}
    ]

    def download_file(url, dest_path):
        """Скачивает файл по URL и сохраняет по указанному пути."""
        try:
            print(f"Скачивание {dest_path} из {url} ...")
            urllib.request.urlretrieve(url, dest_path)
            print("Загрузка завершена.")
            return True
        except Exception as e:
            print(f"Ошибка при скачивании: {e}")
            return False

    # Проверяем каждый файл
    for file_info in critical_files:
        file_path = os.path.join(root_dir, file_info['path'])
        if not os.path.exists(file_path):
            print(f"Критический файл {file_path} не найден. Начинаем загрузку...")
            success = download_file(file_info['url'], file_path)
            if not success:
                print(f"Не удалось загрузить {file_info['path']}. Программа не может продолжить работу.")
                sys.exit(1)
            # Дополнительная проверка, что файл действительно появился
            if not os.path.exists(file_path):
                print(f"Файл {file_path} не был создан после загрузки. Завершение работы.")
                sys.exit(1)
            print(f"Файл {file_info['path']} успешно загружен.")
        else:
            print(f"Файл {file_path} уже существует.")

    # ---------------------- Конец блока проверки ----------------------------

    app, socketio = create_app()

    # Путь к иконке
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')

    # Чтение начального значения always_on_top
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    config_path = os.path.join(parent_dir, 'config.json')
    print(config_path)
    always_on_top = False
    print(f"существование cfg path: {os.path.exists(config_path)}")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(config)
                always_on_top = config.get('overlay', {}).get('always_on_top', False)
                print(config.get('overlay', {}).get('always_on_top', False))
        except Exception:
            pass

    def run_flask():
        socketio.run(app, host='127.0.0.1', port=5001, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    run_window('http://127.0.0.1:5001',
               title='TwitchAssist',
               width=1200,
               height=800,
               icon_path=icon_path,
               always_on_top=always_on_top)

if __name__ == '__main__':
    main()