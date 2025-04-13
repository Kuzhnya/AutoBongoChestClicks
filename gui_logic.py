import tkinter as tk
from tkinter import ttk
import json
import os

def apply_dark_theme(root, style):
    style.theme_use("default")
    style.configure("TLabel", background="#2A2D3E", foreground="#D8DEE9")
    style.configure("TFrame", background="#2A2D3E")
    style.configure("Custom.TCheckbutton", background="#2A2D3E", foreground="#D8DEE9")

def apply_light_theme(root, style):
    style.theme_use("default")
    style.configure("TLabel", background="#F5F7FA", foreground="#2E3440")
    style.configure("TFrame", background="#F5F7FA")
    style.configure("Custom.TCheckbutton", background="#F5F7FA", foreground="#2E3440")

def save_settings(settings):
    try:
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")

def load_settings(default_settings):
    try:
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                for key, value in default_settings.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        return default_settings
    except Exception as e:
        print(f"Error loading settings: {e}")
        return default_settings
