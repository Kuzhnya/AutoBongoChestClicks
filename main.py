import pyautogui
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import winsound
import threading
from pyautogui import ImageNotFoundException
from datetime import datetime

class AutoClicker:
    def __init__(self):
        self.image_path = None
        self.running = False
        self.thread = None
        self.click_count = 0
        self.delay_after_disappear = 0.1
        self.clicks_per_target = 1
        self.click_delay = 0.2

        # GUI
        self.root = tk.Tk()
        self.root.title("Автокликер по картинке")
        self.root.geometry("420x450")

        tk.Button(self.root, text="Выбрать изображение", command=self.select_image).pack(pady=10)

        self.start_button = tk.Button(self.root, text="Старт", command=self.start, state=tk.DISABLED)
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(self.root, text="Стоп", command=self.stop, state=tk.DISABLED)
        self.stop_button.pack(pady=10)

        self.status_label = tk.Label(self.root, text="Изображение не выбрано")
        self.status_label.pack(pady=5)

        self.counter_label = tk.Label(self.root, text="Кликов: 0")
        self.counter_label.pack(pady=5)

        # Задержка после исчезновения изображения
        self.delay_label = tk.Label(self.root, text=f"Задержка после исчезновения (сек): {self.delay_after_disappear:.1f}")
        self.delay_label.pack()
        self.delay_slider = tk.Scale(self.root, from_=0.0, to=2.0, resolution=0.1, orient=tk.HORIZONTAL,
                                     command=self.update_delay_after)
        self.delay_slider.set(self.delay_after_disappear)
        self.delay_slider.pack(pady=5)

        # Кол-во кликов
        self.clicks_label = tk.Label(self.root, text=f"Кликов за раз: {self.clicks_per_target}")
        self.clicks_label.pack()
        self.clicks_slider = tk.Scale(self.root, from_=1, to=10, resolution=1, orient=tk.HORIZONTAL,
                                      command=self.update_clicks)
        self.clicks_slider.set(self.clicks_per_target)
        self.clicks_slider.pack(pady=5)

        # Задержка между кликами
        self.click_delay_label = tk.Label(self.root, text=f"Задержка между кликами (сек): {self.click_delay:.2f}")
        self.click_delay_label.pack()
        self.click_delay_slider = tk.Scale(self.root, from_=0.0, to=1.0, resolution=0.05, orient=tk.HORIZONTAL,
                                           command=self.update_click_delay)
        self.click_delay_slider.set(self.click_delay)
        self.click_delay_slider.pack(pady=5)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def update_delay_after(self, val):
        self.delay_after_disappear = float(val)
        self.delay_label.config(text=f"Задержка после исчезновения (сек): {self.delay_after_disappear:.1f}")

    def update_clicks(self, val):
        self.clicks_per_target = int(val)
        self.clicks_label.config(text=f"Кликов за раз: {self.clicks_per_target}")

    def update_click_delay(self, val):
        self.click_delay = float(val)
        self.click_delay_label.config(text=f"Задержка между кликами (сек): {self.click_delay:.2f}")

    def select_image(self):
        path = filedialog.askopenfilename(title="Выберите изображение",
                                          filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if path:
            self.image_path = path
            self.status_label.config(text=f"Изображение выбрано:\n{path}")
            self.start_button.config(state=tk.NORMAL)

    def start(self):
        if not self.image_path:
            messagebox.showerror("Ошибка", "Сначала выберите изображение!")
            return
        self.running = True
        self.click_count = 0
        self.update_counter()
        self.thread = threading.Thread(target=self.run_bot, daemon=True)
        self.thread.start()
        self.status_label.config(text="Работает...")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

    def stop(self):
        self.running = False
        self.status_label.config(text="Остановлено")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def update_counter(self):
        self.counter_label.config(text=f"Кликов: {self.click_count}")

    def log_click(self, position):
        with open("click_log.txt", "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] Клик по: {position}\n")

    def run_bot(self):
        confidence = 0.8
        time.sleep(1)
        while self.running:
            location = None
            while self.running and location is None:
                try:
                    location = pyautogui.locateCenterOnScreen(self.image_path, confidence=confidence)
                except ImageNotFoundException:
                    pass
                time.sleep(0.1)

            if not self.running:
                break

            for _ in range(self.clicks_per_target):
                pyautogui.click(location)
                self.click_count += 1
                self.update_counter()
                self.log_click(location)
                time.sleep(self.click_delay)

            # Ждём пока изображение исчезнет
            while self.running:
                try:
                    still_there = pyautogui.locateOnScreen(self.image_path, confidence=confidence)
                except ImageNotFoundException:
                    still_there = False

                if not still_there:
                    break
                time.sleep(0.1)

            time.sleep(self.delay_after_disappear)

    def on_close(self):
        self.stop()
        self.root.destroy()

if __name__ == "__main__":
    AutoClicker()
