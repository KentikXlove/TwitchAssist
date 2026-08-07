#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Универсальный билдер для сборки Python проектов в exe.
Конфигурация через файл build_config.json
"""

import os
import sys
import json
import argparse
import shutil
from pathlib import Path


# ----------------------------------------------------------------------
# Загрузка конфигурации
# ----------------------------------------------------------------------
def load_config(config_file='build_program.json'):
    """Загружает конфигурацию из JSON файла."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file)

    if not os.path.exists(config_path):
        # Создаем конфигурацию по умолчанию
        default_config = {
            "project_name": "TwithChat",
            "main_script": "run.py",
            "output_dir": "dist",
            "build_mode": "onedir",  # or "onefile"
            "console": False,
            "clean_build": True,
            "additional_files": [
                {
                    "source": "templates",
                    "destination": "templates",
                    "type": "directory"
                }
            ],
            "additional_binary_files": [],
            "hidden_imports": [],
            "exclude_modules": [],
            "icon": "icon.ico",  # путь к .ico файлу
            "version_file": None,  # путь к .txt файлу с версией
            "upx": True,  # использовать UPX для сжатия
            "runtime_hooks": [],
            "pathex": [],
            "datas": []
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)

        print(f"[ИНФО] Создан файл конфигурации: {config_path}")
        print("[ИНФО] Отредактируйте его и запустите сборку снова.")
        sys.exit(0)

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ОШИБКА] Неверный формат JSON в {config_path}: {e}")
        sys.exit(1)


# ----------------------------------------------------------------------
# Проверка наличия PyInstaller
# ----------------------------------------------------------------------
def check_pyinstaller():
    """Проверяет наличие PyInstaller."""
    try:
        import PyInstaller
        return True
    except ImportError:
        print("[ОШИБКА] PyInstaller не установлен.")
        print("Установите его: pip install pyinstaller")
        return False


# ----------------------------------------------------------------------
# Построение списка данных для --add-data
# ----------------------------------------------------------------------
def build_data_list(config, project_root):
    """
    Формирует список данных для PyInstaller из конфигурации.
    Возвращает список строк в формате "source;destination"
    """
    data_list = []

    # Добавляем файлы из конфигурации
    for item in config.get('additional_files', []):
        source = os.path.join(project_root, item['source'])
        dest = item['destination']

        if not os.path.exists(source):
            print(f"[ПРЕДУПРЕЖДЕНИЕ] Файл/папка не найдены: {source}")
            continue

        data_list.append(f"{source}{os.pathsep}{dest}")

    # Добавляем пользовательские данные
    for data_item in config.get('datas', []):
        source = data_item.get('source')
        dest = data_item.get('destination', '')
        if source and os.path.exists(os.path.join(project_root, source)):
            data_list.append(f"{os.path.join(project_root, source)}{os.pathsep}{dest}")

    return data_list


# ----------------------------------------------------------------------
# Основная функция сборки
# ----------------------------------------------------------------------
def build_project(config_file='build_config.json', extra_args=None):
    """
    Собирает проект согласно конфигурации.
    """
    # Загружаем конфигурацию
    config = load_config(config_file)
    project_root = os.path.dirname(os.path.abspath(__file__))

    # Проверяем PyInstaller
    if not check_pyinstaller():
        sys.exit(1)

    # Проверяем основной скрипт
    main_script = os.path.join(project_root, config.get('main_script', 'run.py'))
    if not os.path.isfile(main_script):
        print(f"[ОШИБКА] Главный скрипт не найден: {main_script}")
        sys.exit(1)

    # Базовые опции
    opts = [
        main_script,
        f'--name={config.get("project_name", "MyApp")}',
        '--noconfirm',
    ]

    # Очистка перед сборкой
    if config.get('clean_build', True):
        opts.append('--clean')

    # Режим сборки
    build_mode = config.get('build_mode', 'onedir')
    if build_mode == 'onefile':
        opts.append('--onefile')
    else:
        opts.append('--onedir')

    # Консольное окно
    if not config.get('console', False):
        opts.append('--windowed')

    # Иконка
    icon = config.get('icon')
    if icon:
        icon_path = os.path.join(project_root, icon)
        if os.path.isfile(icon_path):
            opts.extend(['--icon', icon_path])
        else:
            print(f"[ПРЕДУПРЕЖДЕНИЕ] Иконка не найдена: {icon_path}")

    # Версия
    version_file = config.get('version_file')
    if version_file:
        version_path = os.path.join(project_root, version_file)
        if os.path.isfile(version_path):
            opts.extend(['--version-file', version_path])
        else:
            print(f"[ПРЕДУПРЕЖДЕНИЕ] Файл версии не найден: {version_path}")

    # Добавляем данные
    data_list = build_data_list(config, project_root)
    for data_spec in data_list:
        opts.extend(['--add-data', data_spec])

    # Добавляем бинарные файлы
    for binary_item in config.get('additional_binary_files', []):
        source = os.path.join(project_root, binary_item.get('source', ''))
        dest = binary_item.get('destination', '.')
        if os.path.exists(source):
            opts.extend(['--add-binary', f"{source}{os.pathsep}{dest}"])

    # Скрытые импорты
    for hidden_import in config.get('hidden_imports', []):
        opts.extend(['--hidden-import', hidden_import])

    # Исключаемые модули
    for exclude in config.get('exclude_modules', []):
        opts.extend(['--exclude-module', exclude])

    # UPX сжатие
    if config.get('upx', True):
        opts.append('--upx-dir')
        opts.append('C:\\upx')  # измените на ваш путь к UPX или удалите эту опцию

    # Пути для поиска
    for path in config.get('pathex', []):
        opts.extend(['--paths', os.path.join(project_root, path)])

    # Хуки времени выполнения
    for hook in config.get('runtime_hooks', []):
        hook_path = os.path.join(project_root, hook)
        if os.path.isfile(hook_path):
            opts.extend(['--runtime-hook', hook_path])

    # Дополнительные аргументы из командной строки
    if extra_args:
        opts.extend(extra_args)

    # Вывод информации о сборке
    print("\n" + "=" * 70)
    print("🔨 СБОРКА ПРОЕКТА")
    print("=" * 70)
    print(f"📁 Проект: {config.get('project_name', 'MyApp')}")
    print(f"📄 Главный скрипт: {main_script}")
    print(f"📦 Режим: {'Один файл' if build_mode == 'onefile' else 'Папка с файлами'}")
    print(f"🖥️  Консоль: {'Показать' if config.get('console', False) else 'Скрыть'}")
    print(f"📂 Выходная папка: {config.get('output_dir', 'dist')}")

    if data_list:
        print(f"\n📎 Включаемые файлы/папки:")
        for data in data_list:
            print(f"   • {data}")

    if config.get('hidden_imports'):
        print(f"\n🔍 Скрытые импорты:")
        for imp in config.get('hidden_imports'):
            print(f"   • {imp}")

    print("\n" + "=" * 70)
    print("Команда PyInstaller:")
    print("pyinstaller " + " ".join(opts))
    print("=" * 70 + "\n")

    # Запускаем PyInstaller
    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(opts)

        print("\n✅ СБОРКА УСПЕШНО ЗАВЕРШЕНА!")

        # Показываем где находится exe
        output_dir = config.get('output_dir', 'dist')
        exe_name = config.get('project_name', 'MyApp')

        if build_mode == 'onefile':
            exe_path = os.path.join(project_root, output_dir, f'{exe_name}.exe')
        else:
            exe_path = os.path.join(project_root, output_dir, exe_name, f'{exe_name}.exe')

        if os.path.exists(exe_path):
            print(f"📌 Исполняемый файл: {exe_path}")
        else:
            print(f"📌 Исполняемый файл должен быть в: {exe_path}")

    except Exception as e:
        print(f"\n❌ ОШИБКА СБОРКИ: {e}")
        sys.exit(1)


# ----------------------------------------------------------------------
# Создание примера конфигурации
# ----------------------------------------------------------------------
def create_example_config():
    """Создает пример конфигурационного файла."""
    example = {
        "project_name": "ChatTwith",
        "main_script": "run.py",
        "output_dir": "dist",
        "build_mode": "onedir",  # "onedir" или "onefile"
        "console": False,  # False - скрыть консоль
        "clean_build": True,  # Очищать временные файлы

        # Файлы и папки для включения в сборку
        "additional_files": [
            {"source": "templates", "destination": "templates", "type": "directory"},
            {"source": "logger.py", "destination": ".", "type": "file"},
            {"source": "settings.py", "destination": ".", "type": "file"},
            {"source": "window.py", "destination": ".", "type": "file"},
            {"source": "parser.py", "destination": ".", "type": "file"},
            {"source": "web.py", "destination": ".", "type": "file"},
            {"source": "data/config.py", "destination": ".", "type": "file"},

        ],

        # Бинарные файлы (dll, so, dylib)
        "additional_binary_files": [
            # {"source": "libs/some.dll", "destination": "."}
        ],

        # Скрытые импорты (для динамически загружаемых модулей)
        "hidden_imports": [
            "PyQt5.sip",
            "cffi",
            "cryptography.hazmat.backends.default_backend",
            # Добавьте модули, которые PyInstaller не видит автоматически
        ],

        # Модули для исключения из сборки (уменьшает размер)
        "exclude_modules": [
            # "tkinter",
            # "numpy",
        ],

        # Путь к иконке .ico
        "icon": "icon.ico",  # "app.ico",

        # Файл с информацией о версии
        "version_file": None,  # "version.txt",

        # Использовать UPX сжатие (требуется установленный UPX)
        "upx": False,  # Измените на True если установлен UPX

        # Хуки времени выполнения
        "runtime_hooks": [],

        # Дополнительные пути для поиска модулей
        "pathex": [],

        # Дополнительные данные (расширенный формат)
        "datas": []
    }

    config_path = 'build_program.json'

    if not os.path.exists(config_path):
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(example, f, indent=4, ensure_ascii=False)
        print(f"✅ Создан пример конфигурации: {config_path}")
        print("Отредактируйте его под свой проект и запустите сборку снова.")
        sys.exit(0)


# ----------------------------------------------------------------------
# Точка входа
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Универсальный билдер для Python проектов')
    parser.add_argument('--config', default='build_config.json',
                        help='Путь к файлу конфигурации (по умолчанию: build_config.json)')
    parser.add_argument('--create-example', action='store_true',
                        help='Создать пример конфигурационного файла')
    parser.add_argument('--extra', nargs='*', default=[],
                        help='Дополнительные аргументы для PyInstaller')

    args = parser.parse_args()

    if args.create_example:
        create_example_config()
        return

    # Проверяем наличие конфига
    if not os.path.exists(args.config) and not args.create_example:
        print(f"[ИНФО] Файл конфигурации {args.config} не найден.")
        print("Создаю пример конфигурации...")
        create_example_config()
        return

    # Запускаем сборку
    build_project(args.config, args.extra)


if __name__ == '__main__':
    main()