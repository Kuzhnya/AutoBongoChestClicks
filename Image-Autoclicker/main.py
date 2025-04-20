import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pyautogui
import threading
import time
import os
import winreg
import json
import pystray
import tkinterdnd2
from tkinterdnd2 import *
from PIL import Image, ImageTk
import sys
import ctypes as ct
import shutil
import tempfile
import webbrowser
from gui_logic import save_settings, load_settings, apply_dark_theme, apply_light_theme
from custom_widgets import CustomSlider, CustomButton, CustomNotebook, CustomDropdown, CustomSwitch, CustomListBox, CustomEntry, CustomHotkeyButton
import mss
import numpy as np
import cv2
import keyboard
import logging
import atexit

# Настраиваем логирование
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Определяем путь к приложению
if getattr(sys, 'frozen', False):
    # Если приложение упаковано (PyInstaller)
    app_dir = os.path.dirname(sys.executable)
else:
    # Если запускается как скрипт
    app_dir = os.path.dirname(os.path.abspath(__file__))

# Указываем абсолютный путь для файла лога в директории приложения
log_path = os.path.join(app_dir, "autoclicker_debug.log")
try:
    file_handler = logging.FileHandler(log_path, mode='w')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Добавляем консольный обработчик для отладки (на случай, если файл не создаётся)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logging.debug(f"Logging initialized. Log file: {log_path}")
except Exception as e:
    print(f"Error setting up logging: {e}")


try:
    ct.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

DEFAULT_SETTINGS = {
    "delay_between_clicks": 0.2,
    "delay_after_disappearance": 10.0,
    "clicks_per_cycle": 3,
    "dark_theme": True,
    "language": "RU",
    "autostart": False,
    "image_paths": [],
    "last_image_path": "",
    "window_geometry": "750x847+590+59",
    "search_area": None,
    "click_conditions": {
        "min_images": 1,
        "click_if_not_found": False,
        "max_clicks": 0
    },
    "sequence_mode": True,
    "hotkeys": {
        "start": "f11",
        "stop": "f12"
    }
}

class AutoclickerApp:
    def __init__(self, root):
        self.root = root
        self.has_error = False
        self.is_closing = False  # Флаг, чтобы избежать повторного вызова on_close
        self.info_links = []
        self.settings = load_settings(DEFAULT_SETTINGS)
        # Проверяем, что все ключи из DEFAULT_SETTINGS присутствуют
        for key, value in DEFAULT_SETTINGS.items():
            if key not in self.settings:
                self.settings[key] = value
                logging.warning(f"Missing setting '{key}' in settings, using default: {value}")
        save_settings(self.settings)  # Сохраняем исправленные настройки
        self.languages = self.load_languages()
        self.running = False
        self.image_paths = []
        self.temp_image_paths = []
        self.load_images()
        self.is_minimized = False
        self.icon = None
        self.preview_image = None
        self.delay_scale = None
        self.delay_d_scale = None
        self.click_count_scale = None
        self.delay_text = None
        self.delay_d_text = None
        self.click_count_text = None
        self.status_text = None
        self.drag_start_index = None
        self.is_preview_active = False
        self.search_area = self.settings.get("search_area")
        self.click_conditions = self.settings.get("click_conditions", DEFAULT_SETTINGS["click_conditions"])
        self.sequence_mode = tk.BooleanVar(value=self.settings.get("sequence_mode", False))
        self.hotkeys = self.settings.get("hotkeys", DEFAULT_SETTINGS["hotkeys"])
        self.waiting_for_hotkey = None
        self.total_clicks = 0
        self.sct = mss.mss()
        self.monitors = self.sct.monitors
        self.setup_ui()
        self.apply_theme()
        self.setup_hotkeys()
        atexit.register(self.on_close)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        if self.is_startup_launch() and self.settings["autostart"]:
            logging.debug("Autostart detected.")
            logging.debug(f"sys.argv: {sys.argv}")
            logging.debug(f"temp_image_paths: {self.temp_image_paths}")
            if self.temp_image_paths:
                logging.info("Autostart: starting clicks with %d images", len(self.temp_image_paths))
                self.status_text.set(self.languages[self.settings["language"]]["status_running"])
                self.minimize_to_tray()
                self.start_clicking()
            else:
                logging.info("Autostart: no images, minimized to tray")
                self.minimize_to_tray()
        else:
            logging.debug("Not an autostart launch. Starting in window mode.")
            self.root.deiconify()

    def load_languages(self):
        try:
            with open("languages.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading languages: {e}")
            return {
                "RU": {
                    "title": "Автокликер по изображению",
                    "tab_main": "Основное",
                    "tab_settings": "Настройки",
                    "tab_info": "О программе",
                    "choose_image": "Выбрать изображение",
                    "remove_image": "Удалить изображение",
                    "clear_list": "Очистить список",
                    "select_area": "Выбрать область",
                    "clear_area": "Сбросить область",
                    "configure_conditions": "Настроить условия",
                    "no_image": "Файл не выбран",
                    "start": "Старт",
                    "stop": "Стоп",
                    "dark_theme": "Тёмная тема",
                    "language": "Язык интерфейса:",
                    "autostart": "Автозапуск с Windows",
                    "sequence_mode": "Режим последовательности",
                    "conditions_window_title": "Настройка условий кликов",
                    "min_images_label": "Минимальное количество изображений для клика:",
                    "click_if_not_found": "Кликать, если изображение НЕ найдено",
                    "max_clicks_label": "Максимальное количество кликов (0 = без ограничений):",
                    "apply_conditions": "Применить",
                    "hotkeys_info": "Горячие клавиши: {start} - Старт, {stop} - Стоп",
                    "hotkeys_label": "Настройка горячих клавиш:",
                    "start_hotkey_label": "Клавиша для старта:",
                    "stop_hotkey_label": "Клавиша для стопа:",
                    "apply_hotkeys": "Применить",
                    "info": {
                        "header": "Автокликер по изображению\nDeveloped by Kuzhnya",
                        "links": [
                            {"label": "Github", "url": "https://github.com/Kuzhnya"},
                            {"label": "Twitch.tv", "url": "https://www.twitch.tv/kuzhnya"},
                            {"label": "Discord", "url": "https://discord.gg/3CtQVF7gXM"},
                            {"label": "Telegram", "url": "https://t.me/kuzhnya"},
                            {"label": "Steam", "url": "https://steamcommunity.com/id/Kuzhnya/"}
                        ]
                    },
                    "error_no_image": "Сначала выберите изображение",
                    "delay_clicks": "Задержка между кликами (сек):",
                    "delay_disappear": "Задержка после исчезновения (сек):",
                    "clicks_cycle": "Кликов за цикл:",
                    "status_running": "Программа работает",
                    "status_stopped": "Программа остановлена",
                    "minimize_notification": "Программа будет свёрнута в трей. Чтобы закрыть её, используйте меню в трее.",
                    "confirm_clear_list": "Вы уверены, что хотите очистить список?",
                    "warning": "Предупреждение",
                    "invalid_hotkey": "Недопустимая клавиша! Выберите другую клавишу (Enter и прочие коммандные клавиши не поддерживаются).",
                    "hotkey_conflict": "Эта клавиша уже назначена для другой функции!",
                    "area_cleared_message": "Область поиска очищена. Теперь поиск будет выполняться по всему экрану.",
                    "restore": "Восстановить",  # Добавляем ключ
                    "exit": "Выход"  # Добавляем ключ
                },
                "ENG": {
                    "title": "Image Autoclicker",
                    "tab_main": "Main",
                    "tab_settings": "Settings",
                    "tab_info": "About",
                    "choose_image": "Choose Image",
                    "remove_image": "Remove Image",
                    "clear_list": "Clear List",
                    "select_area": "Select Area",
                    "clear_area": "Clear Area",
                    "configure_conditions": "Configure Conditions",
                    "no_image": "No file selected",
                    "start": "Start",
                    "stop": "Stop",
                    "dark_theme": "Dark Mode",
                    "language": "Interface Language:",
                    "autostart": "Run at Windows Startup",
                    "sequence_mode": "Sequence Mode",
                    "conditions_window_title": "Configure Click Conditions",
                    "min_images_label": "Minimum number of images to click:",
                    "click_if_not_found": "Click if image is NOT found",
                    "max_clicks_label": "Maximum number of clicks (0 = unlimited):",
                    "apply_conditions": "Apply",
                    "hotkeys_info": "Hotkeys: {start} - Start, {stop} - Stop",
                    "hotkeys_label": "Configure Hotkeys:",
                    "start_hotkey_label": "Start Hotkey:",
                    "stop_hotkey_label": "Stop Hotkey:",
                    "apply_hotkeys": "Apply",
                    "info": {
                        "header": "Image AutoClicker\nDeveloped by Kuzhnya",
                        "links": [
                            {"label": "Github", "url": "https://github.com/Kuzhnya"},
                            {"label": "Twitch.tv", "url": "https://www.twitch.tv/kuzhnya"},
                            {"label": "Discord", "url": "https://discord.gg/3CtQVF7gXM"},
                            {"label": "Telegram", "url": "https://t.me/kuzhnya"},
                            {"label": "Steam", "url": "https://steamcommunity.com/id/Kuzhnya/"}
                        ]
                    },
                    "error_no_image": "Please select an image first",
                    "delay_clicks": "Delay between clicks (sec):",
                    "delay_disappear": "Delay after disappearance (sec):",
                    "clicks_cycle": "Clicks per cycle:",
                    "status_running": "Program is running",
                    "status_stopped": "Program is stopped",
                    "minimize_notification": "The program will be minimized to the tray. To close it, use the tray menu.",
                    "confirm_clear_list": "Are you sure you want to clear the list?",
                    "warning": "Warning",
                    "invalid_hotkey": "Invalid key! Choose another key (Enter and Esc are not supported).",
                    "hotkey_conflict": "This key is already assigned to another function!",
                    "area_cleared_message": "Search area has been cleared. Search will now be performed on the entire screen.",
                    "restore": "Restore",  # Добавляем ключ
                    "exit": "Exit"  # Добавляем ключ
                }
            }

    def load_images(self):
        original_paths = self.settings.get("image_paths", [])
        self.image_paths = []
        self.temp_image_paths = []
        logging.debug(f"Loading images from settings: {original_paths}")
        for path in original_paths:
            if os.path.exists(path):
                try:
                    temp_path = os.path.join(tempfile.gettempdir(),
                                             f"autoclicker_temp_{len(self.temp_image_paths)}.png")
                    shutil.copy2(path, temp_path)
                    self.image_paths.append(path)
                    self.temp_image_paths.append(temp_path)
                    logging.debug(f"Successfully loaded image: {path}, temp_path: {temp_path}")
                except Exception as e:
                    logging.error(f"Error copying image {path}: {e}")
            else:
                logging.warning(f"Image file not found: {path}")
        if not self.image_paths:
            logging.warning("No valid images loaded.")

    def setup_hotkeys(self):
        keyboard.unhook_all()
        keyboard.add_hotkey(self.hotkeys["start"], self.start_clicking)
        keyboard.add_hotkey(self.hotkeys["stop"], self.stop_clicking)
        lang = self.settings["language"]
        self.hotkeys_label.config(
            text=self.languages[lang]["hotkeys_info"].format(
                start=self.hotkeys["start"].upper(),
                stop=self.hotkeys["stop"].upper()
            )
        )

    def setup_ui(self):
        self.root.title(self.languages[self.settings["language"]]["title"])
        self.root.geometry(self.settings.get("window_geometry", "900x900+100+100"))
        self.root.minsize(520, 500)
        # Устанавливаем иконку для окна и панели задач
        try:
            # Определяем путь к иконке, не требуя её наличия рядом с исполняемым файлом
            if getattr(sys, 'frozen', False):
                # Если приложение упаковано (например, через PyInstaller)
                icon_path = os.path.join(sys._MEIPASS, "kuzhnya.ico")
            else:
                # Если запускается как скрипт
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kuzhnya.ico")

            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                # Устанавливаем иконку для окна (включая панель задач)
                img = Image.open(icon_path)
                photo = ImageTk.PhotoImage(img)
                self.root.wm_iconphoto(True, photo)
            else:
                print(f"Icon file not found at: {icon_path}")
        except Exception as e:
            print(f"Error setting window icon: {e}")

        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        header_frame = tk.Frame(self.main_frame)
        header_frame.pack(fill="x", padx=5, pady=(5, 0))

        inner_frame = tk.Frame(header_frame)
        inner_frame.pack(fill="both", expand=True)

        self.notebook = CustomNotebook(inner_frame, dark_theme=self.settings["dark_theme"])
        self.notebook.pack(fill="both", expand=False)

        self.tab_main = tk.Frame(inner_frame, bg="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA")
        self.notebook.add(self.tab_main, text=self.languages[self.settings["language"]]["tab_main"])

        self.image_frame = tk.Frame(self.tab_main, bg="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA")
        self.image_frame.pack(fill="x", padx=5, pady=5)

        self.image_button = CustomButton(
            self.image_frame,
            text=self.languages[self.settings["language"]]["choose_image"],
            command=self.add_image,
            dark_theme=self.settings["dark_theme"],
            width=180, height=40
        )
        self.image_button.pack(side="left", padx=(0, 10))

        self.remove_button = CustomButton(
            self.image_frame,
            text=self.languages[self.settings["language"]]["remove_image"],
            command=self.remove_image,
            dark_theme=self.settings["dark_theme"],
            width=180, height=40
        )
        self.remove_button.pack(side="left", padx=(0, 10))

        self.clear_button = CustomButton(
            self.image_frame,
            text=self.languages[self.settings["language"]]["clear_list"],
            command=self.clear_list,
            dark_theme=self.settings["dark_theme"],
            width=180, height=40
        )
        self.clear_button.pack(side="left")

        self.listbox_frame = tk.Frame(self.tab_main, bg="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA")
        self.listbox_frame.pack(padx=5, pady=10)

        self.image_listbox = CustomListBox(
            self.listbox_frame,
            dark_theme=self.settings["dark_theme"],
            width=650
        )
        self.image_listbox.pack(side="left", fill="y", expand=False, padx=(5, 5))

        try:
            self.image_listbox.drop_target_register(DND_FILES)
            self.image_listbox.dnd_bind('<<Drop>>', self.drop_files)
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self.drop_files)
        except Exception as e:
            print(f"Error setting up drag-and-drop: {e}")

        for path in self.image_paths:
            self.image_listbox.insert(tk.END, os.path.basename(path))

        self.image_listbox.bind("<<ListboxSelect>>", self.show_image_preview)
        self.image_listbox.bind("<Button-1>", self.start_drag)
        self.image_listbox.bind("<B1-Motion>", self.on_drag)
        self.image_listbox.bind("<ButtonRelease-1>", self.stop_drag)

        self.preview_label = ttk.Label(self.tab_main)
        self.preview_label.pack(pady=15, fill="x", expand=False)

        self.area_frame = tk.Frame(self.tab_main, bg="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA")
        self.area_frame.pack(fill="x", padx=5, pady=5)

        self.select_area_button = CustomButton(
            self.area_frame,
            text=self.languages[self.settings["language"]]["select_area"],
            command=self.select_area,
            dark_theme=self.settings["dark_theme"],
            width=180, height=40
        )
        self.select_area_button.pack(side="left", padx=(0, 10))

        self.clear_area_button = CustomButton(
            self.area_frame,
            text=self.languages[self.settings["language"]]["clear_area"],
            command=self.clear_area,
            dark_theme=self.settings["dark_theme"],
            width=180, height=40
        )
        self.clear_area_button.pack(side="left", padx=(0, 10))

        self.conditions_button = CustomButton(
            self.area_frame,
            text=self.languages[self.settings["language"]]["configure_conditions"],
            command=self.configure_conditions,
            dark_theme=self.settings["dark_theme"],
            width=180, height=40
        )
        self.conditions_button.pack(side="left")

        self.tab_settings = tk.Frame(inner_frame, bg="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA")
        self.notebook.add(self.tab_settings, text=self.languages[self.settings["language"]]["tab_settings"])

        self.dark_theme_var = tk.BooleanVar(value=self.settings.get("dark_theme", True))

        theme_frame = tk.Frame(self.tab_settings, bg=self.tab_settings["bg"])
        theme_frame.pack(fill="x", padx=5, pady=(10, 10))

        self.theme_label = ttk.Label(
            theme_frame,
            text=self.languages[self.settings["language"]]["dark_theme"],
            font=("Segoe UI", 10),
            background=theme_frame["bg"],
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        )
        self.theme_label.pack(side="left")

        self.theme_switch = CustomSwitch(
            theme_frame,
            text="",
            variable=self.dark_theme_var,
            command=self.update_theme_switch,
            dark_theme=self.settings["dark_theme"],
            width=60,
            height=30
        )
        self.theme_switch.pack(side="right")

        auto_frame = tk.Frame(self.tab_settings, bg=self.tab_settings["bg"])
        auto_frame.pack(fill="x", padx=5, pady=(10, 10))

        self.auto_label = ttk.Label(
            auto_frame,
            text=self.languages[self.settings["language"]]["autostart"],
            font=("Segoe UI", 10),
            background=auto_frame["bg"],
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        )
        self.auto_label.pack(side="left")

        self.autostart = tk.BooleanVar(value=self.settings["autostart"])
        self.chk_auto = CustomSwitch(
            auto_frame,
            text="",
            variable=self.autostart,
            command=self.update_autostart,
            dark_theme=self.settings["dark_theme"],
            width=60,
            height=30
        )
        self.chk_auto.pack(side="right")

        seq_frame = tk.Frame(self.tab_settings, bg=self.tab_settings["bg"])
        seq_frame.pack(fill="x", padx=5, pady=(10, 10))

        self.seq_label = ttk.Label(
            seq_frame,
            text=self.languages[self.settings["language"]]["sequence_mode"],
            font=("Segoe UI", 10),
            background=seq_frame["bg"],
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        )
        self.seq_label.pack(side="left")

        self.sequence_switch = CustomSwitch(
            seq_frame,
            text="",
            variable=self.sequence_mode,
            command=self.update_sequence_mode,
            dark_theme=self.settings["dark_theme"],
            width=60,
            height=30
        )
        self.sequence_switch.pack(side="right")

        self.hotkeys_label_settings = ttk.Label(
            self.tab_settings,
            text=self.languages[self.settings["language"]]["hotkeys_label"],
            font=("Segoe UI", 10),
            background=self.tab_settings["bg"],
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        )
        self.hotkeys_label_settings.pack(anchor="w", padx=5, pady=10)

        self.start_hotkey_frame = tk.Frame(self.tab_settings, bg=self.tab_settings["bg"])
        self.start_hotkey_frame.pack(fill="x", padx=5, pady=5)
        self.start_hotkey_label = ttk.Label(
            self.start_hotkey_frame,
            text=self.languages[self.settings["language"]]["start_hotkey_label"],
            font=("Segoe UI", 10),
            background=self.start_hotkey_frame["bg"],
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        )
        self.start_hotkey_label.pack(side="left")
        self.start_hotkey_button = CustomHotkeyButton(
            self.start_hotkey_frame,
            text=self.hotkeys["start"],
            command=lambda: self.start_hotkey_assign("start"),
            dark_theme=self.settings["dark_theme"],
            width=100,
            height=30
        )
        self.start_hotkey_button.pack(side="left", padx=10)

        self.stop_hotkey_frame = tk.Frame(self.tab_settings, bg=self.tab_settings["bg"])
        self.stop_hotkey_frame.pack(fill="x", padx=5, pady=5)
        self.stop_hotkey_label = ttk.Label(
            self.stop_hotkey_frame,
            text=self.languages[self.settings["language"]]["stop_hotkey_label"],
            font=("Segoe UI", 10),
            background=self.stop_hotkey_frame["bg"],
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        )
        self.stop_hotkey_label.pack(side="left")
        self.stop_hotkey_button = CustomHotkeyButton(
            self.stop_hotkey_frame,
            text=self.hotkeys["stop"],
            command=lambda: self.start_hotkey_assign("stop"),
            dark_theme=self.settings["dark_theme"],
            width=100,
            height=30
        )
        self.stop_hotkey_button.pack(side="left", padx=10)

        self.lang_label = ttk.Label(
            self.tab_settings,
            text=self.languages[self.settings["language"]]["language"],
            font=("Segoe UI", 10),
            background=self.tab_settings["bg"],
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        )
        self.lang_label.pack(anchor="w", padx=5, pady=10)

        self.lang_combo = CustomDropdown(
            self.tab_settings,
            values=["RU", "ENG"],
            command=self.update_language,
            dark_theme=self.settings["dark_theme"],
            width=200,
            height=30
        )
        self.lang_combo.set(self.settings["language"])
        self.lang_combo.pack(fill="x", padx=5, pady=10)

        self.spacer_label = tk.Label(
            self.tab_settings,
            text="",
            font=("Segoe UI", 1),
            bg=self.tab_settings["bg"]
        )
        self.spacer_label.pack(pady=50)

        self.tab_info = tk.Frame(inner_frame, bg="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA")
        self.notebook.add(self.tab_info, text=self.languages[self.settings["language"]]["tab_info"])

        self.setup_sliders()
        self.setup_info_tab()
        for label in self.info_links:
            link_fg = "#1e90ff" if self.settings["dark_theme"] else "#0000ff"
            link_bg = "#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA"
            label.config(fg=link_fg, bg=link_bg)

        self.update_theme_button_style()

    def setup_sliders(self):
        lang = self.languages[self.settings["language"]]

        self.delay_text = tk.StringVar()
        self.delay_label = ttk.Label(
            self.tab_main,
            textvariable=self.delay_text,
            font=("Segoe UI", 10),
            background=self.tab_main["bg"],
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        )
        self.delay_label.pack(anchor="w", padx=5, pady=10)
        self.delay_text.set(f"{lang['delay_clicks']} {self.settings['delay_between_clicks']:.2f}")

        self.delay_scale = CustomSlider(
            self.tab_main,
            from_=0.1,
            to=5.0,
            value=self.settings["delay_between_clicks"],
            command=self.update_values,
            dark_theme=self.settings["dark_theme"],
            width=650
        )
        self.delay_scale.pack(fill="x", padx=5, pady=10)

        self.delay_d_text = tk.StringVar()
        self.delay_d_label = ttk.Label(
            self.tab_main,
            textvariable=self.delay_d_text,
            font=("Segoe UI", 10),
            background=self.tab_main["bg"],
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        )
        self.delay_d_label.pack(anchor="w", padx=5, pady=10)
        self.delay_d_text.set(f"{lang['delay_disappear']} {self.settings['delay_after_disappearance']:.2f}")

        self.delay_d_scale = CustomSlider(
            self.tab_main,
            from_=0.1,
            to=10.0,
            value=self.settings["delay_after_disappearance"],
            command=self.update_values,
            dark_theme=self.settings["dark_theme"],
            width=650
        )
        self.delay_d_scale.pack(fill="x", padx=5, pady=10)

        self.click_count_text = tk.StringVar()
        self.click_count_label = ttk.Label(
            self.tab_main,
            textvariable=self.click_count_text,
            font=("Segoe UI", 10),
            background=self.tab_main["bg"],
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        )
        self.click_count_label.pack(anchor="w", padx=5, pady=10)
        self.click_count_text.set(f"{lang['clicks_cycle']} {self.settings['clicks_per_cycle']}")

        self.click_count_scale = CustomSlider(
            self.tab_main,
            from_=1,
            to=10,
            value=self.settings["clicks_per_cycle"],
            command=self.update_values,
            dark_theme=self.settings["dark_theme"],
            width=650
        )
        self.click_count_scale.pack(fill="x", padx=5, pady=10)

        self.bottom_frame = tk.Frame(self.tab_main, bg="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA")
        self.bottom_frame.pack(fill="x", padx=5, pady=15)

        self.start_btn = CustomButton(
            self.bottom_frame,
            text=self.languages[self.settings["language"]]["start"],
            command=self.start_clicking,
            dark_theme=self.settings["dark_theme"],
            width=120, height=40
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = CustomButton(
            self.bottom_frame,
            text=self.languages[self.settings["language"]]["stop"],
            command=self.stop_clicking,
            dark_theme=self.settings["dark_theme"],
            width=120, height=40
        )
        self.stop_btn.pack(side="left")

        self.status_text = tk.StringVar()
        self.status_text.set(self.languages[self.settings["language"]]["status_stopped"])
        self.status_label = ttk.Label(
            self.tab_main,
            textvariable=self.status_text,
            font=("Segoe UI", 10),
            background=self.tab_main["bg"],
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        )
        self.status_label.pack(pady=10, fill="x", expand=False)

        self.hotkeys_label = ttk.Label(
            self.tab_main,
            text=self.languages[self.settings["language"]]["hotkeys_info"].format(
                start=self.hotkeys["start"].upper(),
                stop=self.hotkeys["stop"].upper()
            ),
            font=("Segoe UI", 10),
            background=self.tab_main["bg"],
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        )
        self.hotkeys_label.pack(pady=5, fill="x", expand=False)

    def update_sliders_theme(self):
        for slider in [self.delay_scale, self.delay_d_scale, self.click_count_scale]:
            slider.config(dark_theme=self.settings["dark_theme"])
            slider.redraw()

    def drop_files(self, event):
        files = self.root.splitlist(event.data)
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')) and file not in self.image_paths:
                try:
                    temp_path = os.path.join(tempfile.gettempdir(), f"autoclicker_temp_{len(self.temp_image_paths)}.png")
                    shutil.copy2(file, temp_path)
                    self.image_paths.append(file)
                    self.temp_image_paths.append(temp_path)
                    self.image_listbox.insert(tk.END, os.path.basename(file))
                    self.settings["image_paths"] = self.image_paths
                    save_settings(self.settings)
                    print(f"Listbox size after drop: {self.image_listbox.size()}")
                    self.image_listbox.update_canvas()
                except Exception as e:
                    print(f"Error adding dropped file {file}: {e}")

    def setup_info_tab(self):
        for widget in self.tab_info.winfo_children():
            widget.destroy()

        lang = self.settings["language"]
        info_data = self.languages[lang]["info"]

        header_label = ttk.Label(
            self.tab_info,
            text=info_data["header"],
            justify="center",
            font=("Segoe UI", 12, "bold"),
            background=self.tab_info["bg"],
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        )
        header_label.pack(padx=5, pady=15)

        self.info_links = []
        for link in info_data["links"]:
            link_frame = tk.Frame(self.tab_info, bg="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA")
            link_frame.pack(anchor="w", padx=5, pady=5)

            label = tk.Label(
                link_frame,
                bg="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA",
                text=link["label"],
                fg="#1e90ff" if self.settings["dark_theme"] else "#0000ff",
                cursor="hand2",
                font=("Segoe UI", 10, "underline")
            )
            label.pack()
            label.bind("<Button-1>", lambda e, url=link["url"]: webbrowser.open(url))
            self.info_links.append(label)

    def update_theme_button_style(self):
        bg_color = "#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA"
        fg_color = "#D8DEE9" if self.settings["dark_theme"] else "#2E3440"
        listbox_select_bg = "#5E81AC" if self.settings["dark_theme"] else "#88C0D0"

        # Обновляем тему для CustomListBox
        self.image_listbox.config(dark_theme=self.settings["dark_theme"])
        self.image_listbox.listbox.config(
            bg=bg_color,
            fg=fg_color,
            selectbackground=listbox_select_bg,
            selectforeground=fg_color
        )
        self.image_listbox.redraw()

        # Обновляем фреймы
        for frame in [self.bottom_frame, self.image_frame, self.area_frame, self.listbox_frame,
                      self.tab_main, self.tab_settings, self.tab_info,
                      self.start_hotkey_frame, self.stop_hotkey_frame]:
            frame.config(bg=bg_color)

        # Обновляем фреймы для переключателей
        for frame in [self.theme_switch.master, self.chk_auto.master, self.sequence_switch.master]:
            frame.config(bg=bg_color)

        # Обновляем CustomButton
        for button in [self.image_button, self.remove_button, self.clear_button,
                       self.select_area_button, self.clear_area_button, self.conditions_button,
                       self.start_btn, self.stop_btn]:
            button.config(dark_theme=self.settings["dark_theme"])
            button.redraw()

        # Обновляем CustomSwitch
        for switch in [self.theme_switch, self.chk_auto, self.sequence_switch]:
            switch.config(dark_theme=self.settings["dark_theme"])
            switch.redraw()

        # Обновляем CustomDropdown
        self.lang_combo.config(dark_theme=self.settings["dark_theme"])
        self.lang_combo.redraw()

        # Обновляем CustomHotkeyButton
        for hotkey_button in [self.start_hotkey_button, self.stop_hotkey_button]:
            hotkey_button.config(dark_theme=self.settings["dark_theme"])
            hotkey_button.redraw()

        # Обновляем все ttk.Label на tab_main
        for label in [self.delay_label, self.delay_d_label, self.click_count_label,
                      self.status_label, self.hotkeys_label]:
            label.config(background=bg_color, foreground=fg_color)

        # Обновляем все ttk.Label на tab_settings
        for label in [self.theme_label, self.auto_label, self.seq_label,
                      self.hotkeys_label_settings, self.start_hotkey_label,
                      self.stop_hotkey_label, self.lang_label]:
            label.config(background=bg_color, foreground=fg_color)

        # Обновляем spacer_label
        if hasattr(self, 'spacer_label'):
            self.spacer_label.config(bg=bg_color)

        # Обновляем CustomSlider
        self.update_sliders_theme()

        # Обновляем вкладку Info
        self.setup_info_tab()

        # Обновляем CustomNotebook
        self.notebook.config(dark_theme=self.settings["dark_theme"])
        self.notebook.redraw()

    # def set_dark_title_bar(self):
    #     try:
    #         self.root.update()
    #         DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    #         set_window_attribute = ct.windll.dwmapi.DwmSetWindowAttribute
    #         hwnd = ct.windll.user32.GetParent(self.root.winfo_id())
    #         rendering_policy = DWMWA_USE_IMMERSIVE_DARK_MODE
    #         value = 2
    #         value = ct.c_int(value)
    #         set_window_attribute(hwnd, rendering_policy, ct.byref(value), ct.sizeof(value))
    #
    #         DWMWA_BORDER_COLOR = 34
    #         color = 0x000000
    #         set_window_attribute(hwnd, DWMWA_BORDER_COLOR, ct.byref(ct.c_int(color)), ct.sizeof(ct.c_int))
    #     except Exception as e:
    #         print(f"Error setting dark title bar or border color: {e}")

    def setup_system_tray(self):
        try:
            if getattr(sys, 'frozen', False):
                resource_path = os.path.join(sys._MEIPASS, "kuzhnya.ico")
            else:
                resource_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "kuzhnya.ico")

            logging.debug(f"Looking for icon at: {resource_path}")

            if not os.path.exists(resource_path):
                logging.warning(f"Icon file {resource_path} not found. Using default Tkinter icon.")
                self.icon = pystray.Icon(
                    "ImageAutoclicker",
                    icon=Image.new('RGB', (16, 16), color='blue'),  # Заглушка
                    title=self.languages[self.settings["language"]]["title"],
                    menu=pystray.Menu(
                        pystray.MenuItem(self.languages[self.settings["language"]]["restore"], self.restore_from_tray),
                        pystray.MenuItem(self.languages[self.settings["language"]]["exit"], self.on_close)
                    )
                )
            else:
                image = Image.open(resource_path)
                self.icon = pystray.Icon(
                    "ImageAutoclicker",
                    icon=image,
                    title=self.languages[self.settings["language"]]["title"],
                    menu=pystray.Menu(
                        pystray.MenuItem(self.languages[self.settings["language"]]["restore"], self.restore_from_tray),
                        pystray.MenuItem(self.languages[self.settings["language"]]["exit"], self.on_close)
                    )
                )
            logging.debug("System tray icon created successfully.")
        except Exception as e:
            self.has_error = True
            logging.error(f"Error setting up system tray: {e}")
            self.icon = None

    def is_startup_launch(self):
        return "--startup" in sys.argv

    def minimize_to_tray(self):
        try:
            logging.debug("Attempting to minimize to tray.")
            if not self.icon or not hasattr(self.icon, '_running') or not self.icon._running:
                logging.debug("Setting up system tray.")
                self.setup_system_tray()

            if not self.icon:
                logging.error("Failed to create system tray icon")
                self.has_error = True
                self.root.withdraw()  # Сворачиваем окно, но не разворачиваем
                return

            self.is_minimized = True
            self.root.withdraw()
            lang = self.settings["language"]

            if not hasattr(self, 'icon_thread') or not self.icon_thread.is_alive():
                self.icon_thread = threading.Thread(target=self.icon.run, daemon=True)
                self.icon_thread.start()
                logging.debug("System tray icon thread started.")
                time.sleep(0.5)
            else:
                logging.debug("System tray icon thread already running.")

            logging.debug("Attempting to show tray notification.")
            self.icon.notify(
                message=self.languages[lang]["minimize_notification"],
                title=self.languages[lang]["title"]
            )
            logging.debug("Tray notification sent successfully.")
            logging.debug("Application minimized to tray.")
        except Exception as e:
            self.has_error = True
            logging.error(f"Error minimizing to tray: {e}")
            self.root.withdraw()  # Сворачиваем, но не разворачиваем

    def restore_from_tray(self):
        try:
            self.is_minimized = False
            self.root.deiconify()
            self.root.lift()
            # Останавливаем иконку в трее и сбрасываем её
            if self.icon:
                self.icon.stop()
                self.icon = None  # Сбрасываем иконку, чтобы пересоздать при следующем сворачивании
                logging.debug("System tray icon stopped and reset.")
        except Exception as e:
            logging.error(f"Error restoring from tray: {e}")

    def on_closing(self):
        if self.is_closing:  # Избегаем повторного вызова
            return
        logging.debug("Window close requested")
        self.minimize_to_tray()  # Сворачиваем в трей при закрытии

    def apply_language(self):
        try:
            lang = self.settings["language"]
            self.root.title(self.languages[lang]["title"])
            self.notebook.tab(0, text=self.languages[lang]["tab_main"])
            self.notebook.tab(1, text=self.languages[lang]["tab_settings"])
            self.notebook.tab(2, text=self.languages[lang]["tab_info"])
            self.image_button.text = self.languages[lang]["choose_image"]
            self.image_button.redraw()
            self.remove_button.text = self.languages[lang]["remove_image"]
            self.remove_button.redraw()
            self.clear_button.text = self.languages[lang]["clear_list"]
            self.clear_button.redraw()
            self.select_area_button.text = self.languages[lang]["select_area"]
            self.select_area_button.redraw()
            self.clear_area_button.text = self.languages[lang]["clear_area"]
            self.clear_area_button.redraw()
            self.conditions_button.text = self.languages[lang]["configure_conditions"]
            self.conditions_button.redraw()
            self.start_btn.text = self.languages[lang]["start"]
            self.start_btn.redraw()
            self.stop_btn.text = self.languages[lang]["stop"]
            self.stop_btn.redraw()
            self.lang_label.config(text=self.languages[lang]["language"])
            self.theme_label.config(text=self.languages[lang]["dark_theme"])
            self.auto_label.config(text=self.languages[lang]["autostart"])
            self.seq_label.config(text=self.languages[lang]["sequence_mode"])
            self.hotkeys_label.config(
                text=self.languages[lang]["hotkeys_info"].format(
                    start=self.hotkeys["start"].upper(),
                    stop=self.hotkeys["stop"].upper()
                )
            )
            self.hotkeys_label_settings.config(text=self.languages[lang]["hotkeys_label"])
            self.start_hotkey_label.config(text=self.languages[lang]["start_hotkey_label"])
            self.stop_hotkey_label.config(text=self.languages[lang]["stop_hotkey_label"])
            self.chk_auto.text = self.languages[lang]["autostart"]
            self.sequence_switch.text = self.languages[lang]["sequence_mode"]

            if self.delay_text:
                self.delay_text.set(f"{self.languages[lang]['delay_clicks']} {self.settings['delay_between_clicks']:.2f}")
                self.delay_d_text.set(f"{self.languages[lang]['delay_disappear']} {self.settings['delay_after_disappearance']:.2f}")
                self.click_count_text.set(f"{self.languages[lang]['clicks_cycle']} {self.settings['clicks_per_cycle']}")

            if self.status_text:
                self.status_text.set(self.languages[lang]["status_running"] if self.running else self.languages[lang]["status_stopped"])

            if self.icon:
                self.icon.title = self.languages[lang]["title"]

            self.setup_info_tab()
        except Exception as e:
            print(f"Error applying language: {e}")

    def apply_theme(self):
        try:
            style = ttk.Style()
            if self.settings["dark_theme"]:
                apply_dark_theme(self.root, style)
                self.main_frame.config(bg="#2A2D3E")
                self.root.config(bg="#2A2D3E")
            else:
                apply_light_theme(self.root, style)
                self.main_frame.config(bg="#F5F7FA")
                self.root.config(bg="#F5F7FA")
            self.update_theme_button_style()
            # self.set_dark_title_bar()
        except Exception as e:
            print(f"Error applying theme: {e}")

    def update_language(self, event=None):
        try:
            self.settings["language"] = self.lang_combo.get()
            self.apply_language()
            save_settings(self.settings)
        except Exception as e:
            print(f"Error updating language: {e}")

    def update_autostart(self):
        try:
            self.settings["autostart"] = self.autostart.get()
            self.set_autostart(self.settings["autostart"])
            save_settings(self.settings)
        except Exception as e:
            print(f"Error updating autostart: {e}")

    def update_sequence_mode(self):
        try:
            self.settings["sequence_mode"] = self.sequence_mode.get()
            save_settings(self.settings)
        except Exception as e:
            print(f"Error updating sequence mode: {e}")

    def start_hotkey_assign(self, hotkey_type):
        if hasattr(self, 'waiting_for_hotkey') and self.waiting_for_hotkey:
            return
        self.waiting_for_hotkey = hotkey_type
        self.last_hotkey = self.hotkeys[hotkey_type]
        button = self.start_hotkey_button if hotkey_type == "start" else self.stop_hotkey_button
        button.set_key("Нажмите...")
        self.root.bind("<KeyPress>", lambda event: self.assign_hotkey(event, hotkey_type))
        self.root.focus_set()

    def assign_hotkey(self, event, hotkey_type):
        forbidden_keys = ["enter", "escape", "shift_l", "shift_r", "control_l", "control_r",
                          "alt_l", "alt_r", "caps_lock", "tab", "return"]
        key = event.keysym.lower()

        button = self.start_hotkey_button if hotkey_type == "start" else self.stop_hotkey_button
        self.root.unbind("<KeyPress>")
        self.waiting_for_hotkey = None

        lang = self.settings["language"]

        if key == "escape":
            button.set_key(self.last_hotkey.upper())
            return

        if key in forbidden_keys:
            button.set_key(self.last_hotkey.upper())
            messagebox.showwarning(
                self.languages[lang]["warning"],
                self.languages[lang]["invalid_hotkey"]
            )
            return

        other_hotkey_type = "stop" if hotkey_type == "start" else "start"
        if key == self.hotkeys[other_hotkey_type].lower():
            button.set_key(self.last_hotkey.upper())
            messagebox.showwarning(
                self.languages[lang]["warning"],
                self.languages[lang]["hotkey_conflict"]
            )
            return

        try:
            keyboard.parse_hotkey(key)
        except ValueError:
            button.set_key(self.last_hotkey.upper())
            messagebox.showwarning(
                self.languages[lang]["warning"],
                self.languages[lang]["invalid_hotkey"]
            )
            return

        self.hotkeys[hotkey_type] = key
        button.set_key(key.upper())
        self.settings["hotkeys"] = self.hotkeys.copy()
        save_settings(self.settings)
        self.setup_hotkeys()

    def set_autostart(self, value):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                                 winreg.KEY_ALL_ACCESS)
            app_name = "ImageAutoclicker"

            if getattr(sys, 'frozen', False):
                app_path = f'"{sys.executable}" --startup'
            else:
                app_path = f'"{sys.executable}" "{os.path.abspath(__file__)}" --startup'

            try:
                current_value, _ = winreg.QueryValueEx(key, app_name)
                logging.debug(f"Current autostart value: {current_value}")
            except FileNotFoundError:
                logging.debug("Autostart not set in registry.")

            if value:
                try:
                    current_value, _ = winreg.QueryValueEx(key, app_name)
                    if current_value == app_path:
                        logging.debug("Autostart already set with the same path, skipping update.")
                        winreg.CloseKey(key)
                        return
                except FileNotFoundError:
                    pass
                logging.info(f"Autostart enabled: {app_path}")
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
            else:
                logging.info("Disabling autostart")
                try:
                    winreg.DeleteValue(key, app_name)
                    logging.debug("Autostart disabled.")
                except FileNotFoundError:
                    logging.debug("Autostart was not set, nothing to delete.")

            winreg.CloseKey(key)
        except Exception as e:
            self.has_error = True
            logging.error(f"Error setting autostart: {e}")

    def update_values(self, event=None):
        try:
            if self.delay_scale and self.delay_d_scale and self.click_count_scale:
                self.settings["delay_between_clicks"] = self.delay_scale.get()
                self.settings["delay_after_disappearance"] = self.delay_d_scale.get()
                self.settings["clicks_per_cycle"] = int(self.click_count_scale.get())
                lang = self.settings["language"]
                self.delay_text.set(f"{self.languages[lang]['delay_clicks']} {self.settings['delay_between_clicks']:.2f}")
                self.delay_d_text.set(f"{self.languages[lang]['delay_disappear']} {self.settings['delay_after_disappearance']:.2f}")
                self.click_count_text.set(f"{self.languages[lang]['clicks_cycle']} {self.settings['clicks_per_cycle']}")
                save_settings(self.settings)
        except Exception as e:
            print(f"Error updating values: {e}")

    def add_image(self):
        try:
            file = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")])
            if file and file not in self.image_paths:
                temp_path = os.path.join(tempfile.gettempdir(), f"autoclicker_temp_{len(self.temp_image_paths)}.png")
                shutil.copy2(file, temp_path)
                self.image_paths.append(file)
                self.temp_image_paths.append(temp_path)
                self.image_listbox.insert(tk.END, os.path.basename(file))
                self.settings["image_paths"] = self.image_paths
                save_settings(self.settings)
                print(f"Listbox size after add: {self.image_listbox.size()}")
                self.image_listbox.update_canvas()
        except Exception as e:
            print(f"Error adding image: {e}")

    def remove_image(self):
        try:
            selection = self.image_listbox.curselection()
            if selection:
                index = selection[0]
                self.image_listbox.delete(index)
                temp_path = self.temp_image_paths.pop(index)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                self.image_paths.pop(index)
                self.settings["image_paths"] = self.image_paths
                save_settings(self.settings)
                self.preview_label.config(image=None)
                if not self.image_listbox.size():
                    self.is_preview_active = False
                print(f"Listbox size after remove: {self.image_listbox.size()}")
                self.image_listbox.update_canvas()
        except Exception as e:
            print(f"Error removing image: {e}")

    def clear_list(self):
        try:
            if not self.image_paths:
                return
            lang = self.settings["language"]
            if messagebox.askyesno("Confirm", self.languages[lang]["confirm_clear_list"]):
                for i in range(self.image_listbox.size() - 1, -1, -1):
                    self.image_listbox.delete(i)
                for temp_path in self.temp_image_paths:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                self.image_paths = []
                self.temp_image_paths = []
                self.settings["image_paths"] = self.image_paths
                save_settings(self.settings)
                self.preview_label.config(image=None)
                self.is_preview_active = False
                print(f"Listbox size after clear: {self.image_listbox.size()}")
                self.image_listbox.update_canvas()
        except Exception as e:
            print(f"Error clearing list: {e}")

    def start_drag(self, event):
        index = self.image_listbox.nearest(event.y)
        if index >= 0:
            self.drag_start_index = index
            self.image_listbox.selection_clear(0, tk.END)
            self.image_listbox.selection_set(index)

    def on_drag(self, event):
        if self.drag_start_index is None:
            return
        index = self.image_listbox.nearest(event.y)
        if index >= 0 and index != self.drag_start_index:
            item = self.image_listbox.get(self.drag_start_index)
            temp_path = self.temp_image_paths[self.drag_start_index]
            orig_path = self.image_paths[self.drag_start_index]
            self.image_listbox.delete(self.drag_start_index)
            self.temp_image_paths.pop(self.drag_start_index)
            self.image_paths.pop(self.drag_start_index)
            self.image_listbox.insert(index, item)
            self.temp_image_paths.insert(index, temp_path)
            self.image_paths.insert(index, orig_path)
            self.image_listbox.selection_clear(0, tk.END)
            self.image_listbox.selection_set(index)
            self.drag_start_index = index
            self.settings["image_paths"] = self.image_paths
            save_settings(self.settings)
            print(f"Listbox size after drag: {self.image_listbox.size()}")
            self.image_listbox.update_canvas()

    def stop_drag(self, event):
        self.drag_start_index = None

    def show_image_preview(self, event=None):
        try:
            selection = self.image_listbox.curselection()
            if selection:
                index = selection[0]
                image_path = self.temp_image_paths[index]
                image = Image.open(image_path)
                image.thumbnail((100, 100))
                self.preview_image = ImageTk.PhotoImage(image)
                self.preview_label.config(image=self.preview_image)
                if not self.is_preview_active:
                    self.is_preview_active = True
            else:
                self.preview_label.config(image=None)
                if self.is_preview_active:
                    self.is_preview_active = False
        except Exception as e:
            print(f"Error showing image preview: {e}")

    def select_area(self):
        self.selection_window = tk.Toplevel(self.root)
        self.selection_window.attributes('-fullscreen', True)
        self.selection_window.attributes('-alpha', 0.3)
        self.selection_window.configure(bg='black')

        self.start_x = None
        self.start_y = None
        self.rect = None
        self.monitor_idx = None

        self.selection_canvas = tk.Canvas(self.selection_window, bg='black', highlightthickness=0)
        self.selection_canvas.pack(fill="both", expand=True)

        self.selection_canvas.bind("<Button-1>", self.start_selection)
        self.selection_canvas.bind("<B1-Motion>", self.update_selection)
        self.selection_canvas.bind("<ButtonRelease-1>", self.end_selection)

    def start_selection(self, event):
        self.start_x = self.selection_canvas.winfo_pointerx()
        self.start_y = self.selection_canvas.winfo_pointery()
        for idx, monitor in enumerate(self.monitors):
            if (monitor["left"] <= self.start_x < monitor["left"] + monitor["width"] and
                monitor["top"] <= self.start_y < monitor["top"] + monitor["height"]):
                self.monitor_idx = idx
                break

    def update_selection(self, event):
        if self.start_x is None or self.start_y is None:
            return
        self.selection_canvas.delete("selection")
        end_x = self.selection_canvas.winfo_pointerx()
        end_y = self.selection_canvas.winfo_pointery()
        self.rect = self.selection_canvas.create_rectangle(
            self.start_x, self.start_y, end_x, end_y,
            outline='red', width=2, tags="selection"
        )

    def end_selection(self, event):
        if self.start_x is None or self.start_y is None or self.monitor_idx is None:
            self.selection_window.destroy()
            return
        end_x = self.selection_canvas.winfo_pointerx()
        end_y = self.selection_canvas.winfo_pointery()
        monitor = self.monitors[self.monitor_idx]
        left = min(self.start_x, end_x) - monitor["left"]
        top = min(self.start_y, end_y) - monitor["top"]
        width = abs(self.start_x - end_x)
        height = abs(self.start_y - end_y)
        if width < 10 or height < 10:
            logging.warning("Selected area too small, resetting")
            messagebox.showwarning(
                self.languages[self.settings["language"]]["warning"],
                "Область слишком мала"
            )
            self.search_area = None
            self.settings["search_area"] = None
        else:
            self.search_area = {
                "left": left,
                "top": top,
                "width": width,
                "height": height,
                "monitor_idx": self.monitor_idx
            }
            self.settings["search_area"] = self.search_area
            logging.info(f"Area selected: {self.search_area}")
        save_settings(self.settings)
        self.selection_window.destroy()

    def clear_area(self):
        self.search_area = None
        self.settings["search_area"] = None
        save_settings(self.settings)
        lang = self.settings["language"]
        messagebox.showinfo(
            title=self.languages[lang]["title"],
            message=self.languages[lang]["area_cleared_message"]
        )
        logging.info("Search area cleared")

    def configure_conditions(self):
        self.root.update()
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        # set_window_attribute = ct.windll.dwmapi.DwmSetWindowAttribute
        # hwnd = ct.windll.user32.GetParent(self.root.winfo_id())
        # rendering_policy = DWMWA_USE_IMMERSIVE_DARK_MODE
        # value = 2
        # value = ct.c_int(value)
        # set_window_attribute(hwnd, rendering_policy, ct.byref(value), ct.sizeof(value))
        #
        # DWMWA_BORDER_COLOR = 34
        # color = 0x000000
        # set_window_attribute(hwnd, DWMWA_BORDER_COLOR, ct.byref(ct.c_int(color)), ct.sizeof(ct.c_int))

        conditions_window = tk.Toplevel(self.root)
        conditions_window.title(self.languages[self.settings["language"]]["conditions_window_title"])
        conditions_window.geometry("580x300")
        conditions_window.resizable(False, False)
        conditions_window.transient(self.root)
        conditions_window.grab_set()

        conditions_window.config(bg="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA")
        style = ttk.Style(conditions_window)
        if self.settings["dark_theme"]:
            apply_dark_theme(conditions_window, style)
        else:
            apply_light_theme(conditions_window, style)

        min_images_frame = tk.Frame(
            conditions_window,
            bg="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA"
        )
        min_images_frame.pack(pady=10, fill="x", padx=5)

        min_images_label = ttk.Label(
            min_images_frame,
            text=self.languages[self.settings["language"]]["min_images_label"],
            font=("Segoe UI", 10),
            background="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA",
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440",
            wraplength=350
        )
        min_images_label.pack(side="left", anchor="w")

        min_images_var = tk.StringVar(value=str(self.click_conditions["min_images"]))
        min_images_entry = CustomEntry(
            min_images_frame,
            textvariable=min_images_var,
            dark_theme=self.settings["dark_theme"],
            width=150,
            height=30
        )
        min_images_entry.pack(side="left", padx=(10, 0))

        click_if_not_found_frame = tk.Frame(
            conditions_window,
            bg="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA"
        )
        click_if_not_found_frame.pack(pady=10, fill="x", padx=5)

        click_if_not_found_desc = ttk.Label(
            click_if_not_found_frame,
            text=self.languages[self.settings["language"]]["click_if_not_found"],
            font=("Segoe UI", 10),
            background="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA",
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440",
            wraplength=450
        )
        click_if_not_found_desc.pack(side="left", anchor="w")

        click_if_not_found_var = tk.BooleanVar(value=self.click_conditions["click_if_not_found"])
        click_if_not_found_switch = CustomSwitch(
            click_if_not_found_frame,
            text="",
            variable=click_if_not_found_var,
            dark_theme=self.settings["dark_theme"],
            width=60,
            height=30
        )
        click_if_not_found_switch.pack(side="left", padx=(10, 0))

        max_clicks_frame = tk.Frame(
            conditions_window,
            bg="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA"
        )
        max_clicks_frame.pack(pady=10, fill="x", padx=5)

        max_clicks_label = ttk.Label(
            max_clicks_frame,
            text=self.languages[self.settings["language"]]["max_clicks_label"],
            font=("Segoe UI", 10),
            background="#2A2D3E" if self.settings["dark_theme"] else "#F5F7FA",
            foreground="#D8DEE9" if self.settings["dark_theme"] else "#2E3440",
            wraplength=350
        )
        max_clicks_label.pack(side="left", anchor="w")

        max_clicks_var = tk.StringVar(value=str(self.click_conditions["max_clicks"]))
        max_clicks_entry = CustomEntry(
            max_clicks_frame,
            textvariable=max_clicks_var,
            dark_theme=self.settings["dark_theme"],
            width=150,
            height=30
        )
        max_clicks_entry.pack(side="left", padx=(10, 0))

        apply_button = CustomButton(
            conditions_window,
            text=self.languages[self.settings["language"]]["apply_conditions"],
            command=lambda: self.apply_conditions(
                min_images_var.get(),
                click_if_not_found_var.get(),
                max_clicks_var.get(),
                conditions_window
            ),
            dark_theme=self.settings["dark_theme"],
            width=180, height=40
        )
        apply_button.pack(pady=20)

    def apply_conditions(self, min_images, click_if_not_found, max_clicks, window):
        try:
            min_images = int(min_images)
            max_clicks = int(max_clicks)
            self.click_conditions = {
                "min_images": max(1, min_images),
                "click_if_not_found": click_if_not_found,
                "max_clicks": max(0, max_clicks)
            }
            self.settings["click_conditions"] = self.click_conditions
            save_settings(self.settings)
            window.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for minimum images and maximum clicks.")

    def start_clicking(self):
        logging.debug("start_clicking called")
        if not self.temp_image_paths:
            lang = self.settings["language"]
            messagebox.showerror(
                self.languages[lang]["title"],
                self.languages[lang]["error_no_image"]
            )
            logging.warning("No images available to start clicking")
            return
        if self.click_conditions["min_images"] > len(self.temp_image_paths):
            lang = self.settings["language"]
            messagebox.showerror(
                self.languages[lang]["title"],
                "Недостаточно изображений для минимального условия"
            )
            logging.warning("Start aborted: min_images exceeds loaded images")
            return
        if self.running:
            logging.debug("Clicking already running, skipping")
            return
        self.running = True
        lang = self.settings["language"]
        self.status_text.set(self.languages[lang]["status_running"])
        logging.info("Starting click process")
        threading.Thread(target=self.click_images, daemon=True).start()

    def stop_clicking(self):
        logging.debug("stop_clicking called")
        self.running = False
        self.current_image_idx = 0
        lang = self.settings["language"]
        self.status_text.set(self.languages[lang]["status_stopped"])
        logging.info("Clicking stopped, sequence index reset")

    def click_images(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.01
        sct = mss.mss()
        current_image_idx = 0

        monitors = sct.monitors
        default_monitor = None
        min_distance = float('inf')
        for monitor in monitors[1:]:
            distance = (monitor["left"] ** 2 + monitor["top"] ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                default_monitor = monitor

        if default_monitor is None:
            logging.error("No monitors found. Stopping click process.")
            self.stop_clicking()
            return

        screen_width, screen_height = default_monitor["width"], default_monitor["height"]
        logging.info(f"Screen size: {screen_width}x{screen_height}")

        while self.running:
            found_positions = []
            images_to_search = []

            if self.sequence_mode.get():
                if current_image_idx < len(self.temp_image_paths):
                    images_to_search = [self.temp_image_paths[current_image_idx]]
                else:
                    current_image_idx = 0
                    images_to_search = [self.temp_image_paths[current_image_idx]]
            else:
                images_to_search = self.temp_image_paths

            if self.search_area is not None and "monitor_idx" in self.search_area and self.search_area[
                "monitor_idx"] < len(self.monitors):
                monitor = self.monitors[self.search_area["monitor_idx"]]
                region = {
                    "left": monitor["left"] + self.search_area["left"],
                    "top": monitor["top"] + self.search_area["top"],
                    "width": self.search_area["width"],
                    "height": self.search_area["height"]
                }
                logging.debug(f"Search area: {region}")
            else:
                monitor = default_monitor
                region = {
                    "left": monitor["left"],
                    "top": monitor["top"],
                    "width": monitor["width"],
                    "height": monitor["height"]
                }
                logging.debug(f"Using default monitor: {region}")

            if region["width"] <= 0 or region["height"] <= 0:
                logging.error(f"Invalid region size: {region}. Stopping click process.")
                self.stop_clicking()
                break

            for img_path in images_to_search:
                try:
                    template = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    if template is None:
                        logging.error(f"Failed to load template image: {img_path}")
                        continue

                    screenshot = np.array(sct.grab(region))
                    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)

                    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
                    threshold = 0.7
                    loc = np.where(result >= threshold)

                    for pt in zip(*loc[::-1]):
                        x = pt[0] + template.shape[1] // 2
                        y = pt[1] + template.shape[0] // 2
                        x += region["left"]
                        y += region["top"]
                        x -= default_monitor["left"]
                        y -= default_monitor["top"]
                        x = max(0, min(x, screen_width - 1))
                        y = max(0, min(y, screen_height - 1))
                        found_positions.append((x, y))

                except Exception as e:
                    logging.error(f"Error processing image {img_path}: {e}")

            should_click = False
            logging.debug(
                f"Conditions check: min_images={self.click_conditions['min_images']}, found={len(found_positions)}, click_if_not_found={self.click_conditions['click_if_not_found']}")
            if self.click_conditions["click_if_not_found"]:
                should_click = len(found_positions) == 0
            else:
                should_click = len(found_positions) >= self.click_conditions["min_images"]

            if should_click:
                if self.click_conditions["max_clicks"] > 0 and self.total_clicks >= self.click_conditions["max_clicks"]:
                    logging.info("Max clicks reached, stopping")
                    self.stop_clicking()
                    break

                if found_positions or self.click_conditions["click_if_not_found"]:
                    if not found_positions:
                        if self.search_area is None:
                            logging.warning("No search area for click_if_not_found, skipping")
                            time.sleep(0.1)
                            continue
                        x = region["left"] + region["width"] // 2
                        y = region["top"] + region["height"] // 2
                        x -= default_monitor["left"]
                        y -= default_monitor["top"]
                        x = max(0, min(x, screen_width - 1))
                        y = max(0, min(y, screen_height - 1))
                    else:
                        x, y = found_positions[0]

                    for _ in range(int(self.settings["clicks_per_cycle"])):
                        if not self.running:
                            break
                        pyautogui.click(x, y)
                        self.total_clicks += 1
                        lang = self.settings["language"]
                        status = f"{self.languages[lang]['status_running']} ({self.total_clicks})"
                        if self.sequence_mode.get():
                            status += " (последовательный режим)"
                        self.status_text.set(status)
                        logging.info(f"Click at ({x}, {y}), total_clicks={self.total_clicks}")
                        time.sleep(self.settings["delay_between_clicks"])
                    if self.sequence_mode.get():
                        current_image_idx += 1
                    time.sleep(self.settings["delay_after_disappearance"])
                else:
                    time.sleep(0.1)
            else:
                time.sleep(0.1)

        lang = self.settings["language"]
        self.status_text.set(self.languages[lang]["status_stopped"])

    def update_theme_switch(self):
        self.settings["dark_theme"] = self.dark_theme_var.get()
        save_settings(self.settings)
        self.apply_theme()

    def on_close(self):
        if self.is_closing:
            return
        self.is_closing = True
        logging.debug("Closing application")

        self.stop_clicking()
        logging.debug("Clicking stopped")
        time.sleep(0.1)

        try:
            keyboard.unhook_all()
            logging.debug("Keyboard hooks cleared")
        except Exception as e:
            logging.error(f"Error clearing keyboard hooks: {e}")
            self.has_error = True

        try:
            if hasattr(self, 'sct') and self.sct:
                try:
                    self.sct.close()
                    logging.debug("MSS closed")
                except AttributeError as e:
                    logging.warning(f"Could not close MSS due to attribute error: {e}")
                finally:
                    self.sct = None
        except Exception as e:
            logging.error(f"Unexpected error closing MSS: {e}")
            self.has_error = True

        try:
            if self.icon:
                self.icon.stop()
                self.icon = None
                logging.debug("System tray stopped")
        except Exception as e:
            logging.error(f"Error stopping system tray: {e}")
            self.has_error = True

        try:
            for temp_path in self.temp_image_paths:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            logging.debug("Temporary files removed")
        except Exception as e:
            logging.error(f"Error removing temporary files: {e}")
            self.has_error = True

        try:
            self.root.destroy()
            logging.debug("Root window destroyed")
        except Exception as e:
            logging.error(f"Error destroying root window: {e}")
            self.has_error = True

        if self.has_error:
            logging.info("Errors detected, keeping log file")
        else:
            logging.info("No errors, removing log file")
            try:
                os.remove(log_path)
            except Exception as e:
                logging.error(f"Error removing log file: {e}")

        logging.debug("Exiting application")
        os._exit(0)


def register_exit_handler(app):
    atexit.register(app.on_close)

# Точка входа программы
if __name__ == "__main__":
    logging.debug("Application started with args: %s", sys.argv)
    root = tkinterdnd2.TkinterDnD.Tk()
    app = AutoclickerApp(root)
    register_exit_handler(app)  # Регистрируем обработчик выхода
    root.mainloop()
    app.on_close()  # Вызываем on_close после завершения mainloop
