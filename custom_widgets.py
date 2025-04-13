import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import math
import tkinterdnd2

class CustomSlider(tk.Canvas):
    def __init__(self, parent, from_=0, to=100, value=0, command=None, **kwargs):
        self.dark_theme = kwargs.pop("dark_theme", False)
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.from_ = from_
        self.to = to
        self.value = value
        self.command = command
        self.width = kwargs.get("width", 300)
        self.height = kwargs.get("height", 30)
        self.config(width=self.width, height=self.height)

        self.trough_color = "#3B3F51" if self.dark_theme else "#E4E7EB"
        self.trough_active_color = "#4A5068" if self.dark_theme else "#D9DCE3"
        self.slider_color = "#5E81AC" if self.dark_theme else "#1E90FF"

        self.trough_height = 8
        self.slider_radius = 12
        self.slider_pos = self.value_to_pos(value)

        self.config(bg=self.parent_background())

        self.bind("<Configure>", self.redraw)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)

        self.is_dragging = False
        self.slider_image = None
        self.redraw()

    def parent_background(self):
        try:
            return self.master.cget("bg")
        except:
            return "#2A2D3E" if self.dark_theme else "#F5F7FA"

    def value_to_pos(self, value):
        range_ = self.to - self.from_
        pos_range = self.width - 2 * self.slider_radius
        return (value - self.from_) / range_ * pos_range + self.slider_radius

    def pos_to_value(self, pos):
        range_ = self.to - self.from_
        pos_range = self.width - 2 * self.slider_radius
        return self.from_ + (pos - self.slider_radius) / pos_range * range_

    def redraw(self, event=None):
        self.delete("all")
        self.config(bg=self.parent_background())

        scale = 2
        img_width = int(self.width * scale)
        img_height = int(self.height * scale)
        image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        trough_y = img_height // 2
        trough_height_scaled = self.trough_height * scale
        trough_color = self.trough_active_color if self.is_dragging else self.trough_color
        draw.rectangle(
            (self.slider_radius * scale, trough_y - trough_height_scaled // 2,
             (self.width - self.slider_radius) * scale, trough_y + trough_height_scaled // 2),
            fill=trough_color
        )

        slider_pos_scaled = self.slider_pos * scale
        slider_radius_scaled = self.slider_radius * scale
        draw.ellipse(
            (slider_pos_scaled - slider_radius_scaled, trough_y - slider_radius_scaled,
             slider_pos_scaled + slider_radius_scaled, trough_y + slider_radius_scaled),
            fill=self.slider_color
        )

        image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        self.slider_image = ImageTk.PhotoImage(image)
        self.create_image(0, 0, anchor="nw", image=self.slider_image)

    def on_press(self, event):
        self.is_dragging = True
        self.on_drag(event)

    def on_drag(self, event):
        if not self.is_dragging:
            return
        new_pos = max(self.slider_radius, min(self.width - self.slider_radius, event.x))
        self.slider_pos = new_pos
        self.value = self.pos_to_value(new_pos)
        self.redraw()
        if self.command:
            self.command()

    def on_release(self, event):
        self.is_dragging = False
        self.redraw()

    def get(self):
        return self.value

    def set(self, value):
        self.value = max(self.from_, min(self.to, value))
        self.slider_pos = self.value_to_pos(self.value)
        self.redraw()

    def config(self, **kwargs):
        if "dark_theme" in kwargs:
            self.dark_theme = kwargs.pop("dark_theme")
            self.trough_color = "#3B3F51" if self.dark_theme else "#E4E7EB"
            self.trough_active_color = "#4A5068" if self.dark_theme else "#D9DCE3"
            self.slider_color = "#5E81AC" if self.dark_theme else "#1E90FF"
            self.config(bg=self.parent_background())
            self.redraw()
        super().config(**kwargs)

class CustomButton(tk.Canvas):
    def __init__(self, parent, text, command=None, transparent=False, **kwargs):
        self.dark_theme = kwargs.pop("dark_theme", False)
        self.transparent = transparent
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.text = text
        self.command = command
        self.width = kwargs.get("width", 180)
        self.height = kwargs.get("height", 40)
        self.config(width=self.width, height=self.height)

        self.bg_color = "#3B3F51" if self.dark_theme else "#D3D7E0"
        self.active_bg_color = "#5E81AC" if self.dark_theme else "#88C0D0"
        self.fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"
        self.active_fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"

        self.config(bg=self.parent_background())

        self.is_hovered = False
        self.is_pressed = False
        self.button_image = None
        self.animation_frames = []
        self.current_frame = 0
        self.animation_running = False

        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)

        self.redraw()

    def parent_background(self):
        try:
            return self.master.cget("bg")
        except:
            return "#2A2D3E" if self.dark_theme else "#F5F7FA"

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb):
        return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

    def interpolate_color(self, color1, color2, factor):
        rgb1 = self.hex_to_rgb(color1)
        rgb2 = self.hex_to_rgb(color2)
        new_rgb = tuple(int(rgb1[i] + (rgb2[i] - rgb1[i]) * factor) for i in range(3))
        return self.rgb_to_hex(new_rgb)

    def create_animation_frames(self, start_color, end_color, steps=10):
        self.animation_frames = []
        for i in range(steps):
            factor = i / (steps - 1) if steps > 1 else 1
            color = self.interpolate_color(start_color, end_color, factor)
            self.animation_frames.append(self.draw_button(color))

    def draw_button(self, bg_color):
        scale = 2
        img_width = int(self.width * scale)
        img_height = int(self.height * scale)
        image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        fg_color = self.active_fg_color if (self.is_hovered or self.is_pressed) else self.fg_color
        if not self.transparent:
            self.create_rounded_rect(draw, 0, 0, img_width, img_height, radius=15 * scale, fill=bg_color)
        try:
            font = ImageFont.truetype("segoeui.ttf", 30 * scale // 2)
        except:
            font = None
        draw.text((img_width // 2, img_height // 2), self.text, fill=fg_color, font=font, anchor="mm")

        image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)


    def on_enter(self, event):
        if not self.is_hovered:
            self.is_hovered = True
            self.is_pressed = False
            self.animation_running = True
            self.current_frame = 0
            self.create_animation_frames(self.bg_color, self.active_bg_color)
            self.animate()

    def on_leave(self, event):
        if self.is_hovered:
            self.is_hovered = False
            self.is_pressed = False
            self.animation_running = True
            self.current_frame = 0
            self.create_animation_frames(self.active_bg_color, self.bg_color)
            self.animate()

    def on_press(self, event):
        self.is_pressed = True
        self.redraw()

    def on_release(self, event):
        self.is_pressed = False
        if self.is_hovered:
            self.redraw()  # Обновляем, если курсор всё ещё на кнопке
        else:
            self.is_hovered = False
            self.animation_running = False
            self.redraw()  # Принудительно возвращаем исходный цвет
        if self.command:
            self.command()

    def animate(self):
        if self.current_frame < len(self.animation_frames) and self.animation_running:
            self.button_image = self.animation_frames[self.current_frame]
            self.delete("all")
            self.create_image(0, 0, anchor="nw", image=self.button_image)
            self.current_frame += 1
            self.after(30, self.animate)
        else:
            self.animation_running = False
            self.redraw()  # Гарантируем возврат к правильному цвету

    def redraw(self):
        self.delete("all")
        self.config(bg=self.parent_background())
        bg_color = self.active_bg_color if (self.is_hovered or self.is_pressed) else self.bg_color
        self.button_image = self.draw_button(bg_color)
        self.create_image(0, 0, anchor="nw", image=self.button_image)

    def create_rounded_rect(self, draw, x1, y1, x2, y2, radius, **kwargs):
        draw.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=kwargs.get("fill"), outline=None)

    def config(self, **kwargs):
        if "dark_theme" in kwargs:
            self.dark_theme = kwargs.pop("dark_theme")
            self.bg_color = "#3B3F51" if self.dark_theme else "#D3D7E0"
            self.active_bg_color = "#5E81AC" if self.dark_theme else "#88C0D0"
            self.fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"
            self.active_fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"
            self.config(bg=self.parent_background())
            self.redraw()
        super().config(**kwargs)

class CustomNotebook(tk.Canvas):
    def __init__(self, parent, **kwargs):
        self.dark_theme = kwargs.pop("dark_theme", False)
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.width = kwargs.get("width", 700)
        self.height = kwargs.get("height", 40)
        self.config(width=self.width, height=self.height)

        self.bg_color = "#2A2D3E" if self.dark_theme else "#F5F7FA"
        self.tab_bg_color = "#3B3F51" if self.dark_theme else "#E4E7EB"
        self.tab_active_color = "#5E81AC" if self.dark_theme else "#88C0D0"
        self.tab_text_color = "#D8DEE9" if self.dark_theme else "#2E3440"

        self.config(bg=self.bg_color)

        self.tabs = []
        self.frames = []
        self.current_tab = 0
        self.tab_images = []

        self.bind("<Button-1>", self.on_tab_click)

    def add(self, frame, text):
        self.tabs.append(text)
        self.frames.append(frame)
        self.redraw()

    def redraw(self):
        self.delete("all")
        self.tab_images = []
        tab_width = self.width // max(1, len(self.tabs))
        scale = 2

        for i, tab_text in enumerate(self.tabs):
            x1 = i * tab_width
            x2 = (i + 1) * tab_width
            fill_color = self.tab_active_color if i == self.current_tab else self.tab_bg_color

            img_width = (x2 - x1) * scale
            img_height = self.height * scale
            image = Image.new("RGBA", (int(img_width), int(img_height)), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)

            # Рисуем простой прямоугольник без скругления
            draw.rectangle((0, 0, img_width, img_height), fill=fill_color, outline=None)

            try:
                font = ImageFont.truetype("segoeui.ttf", 30 * scale // 2)
            except:
                font = None
            draw.text((img_width // 2, img_height // 2), tab_text, fill=self.tab_text_color, font=font, anchor="mm")

            image = image.resize((x2 - x1, self.height), Image.Resampling.LANCZOS)
            tab_image = ImageTk.PhotoImage(image)
            self.tab_images.append(tab_image)
            self.create_image(x1, 0, anchor="nw", image=tab_image)

        # Линия под вкладками
        self.create_line(
            0, self.height, self.width, self.height,
            fill=self.tab_bg_color
        )

        for i, frame in enumerate(self.frames):
            frame.pack_forget()  # <- ВСЕГДА сначала скрываем
        self.frames[self.current_tab].pack(fill="both", expand=True)

    def on_tab_click(self, event):
        tab_width = self.width // max(1, len(self.tabs))
        clicked_tab = event.x // tab_width
        if 0 <= clicked_tab < len(self.tabs):
            self.current_tab = clicked_tab
            self.redraw()

    def config(self, **kwargs):
        if "dark_theme" in kwargs:
            self.dark_theme = kwargs.pop("dark_theme")
            self.bg_color = "#2A2D3E" if self.dark_theme else "#F5F7FA"
            self.tab_bg_color = "#3B3F51" if self.dark_theme else "#E4E7EB"
            self.tab_active_color = "#5E81AC" if self.dark_theme else "#88C0D0"
            self.tab_text_color = "#D8DEE9" if self.dark_theme else "#2E3440"
            self.config(bg=self.bg_color)
            self.redraw()
        super().config(**kwargs)

    def tab(self, index, **kwargs):
        if "text" in kwargs:
            self.tabs[index] = kwargs["text"]
            self.redraw()

class CustomDropdown(tk.Canvas):
    def __init__(self, parent, values, command=None, **kwargs):
        self.dark_theme = kwargs.pop("dark_theme", False)
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.values = values
        self.command = command
        self.width = kwargs.get("width", 200)
        self.height = kwargs.get("height", 30)
        self.config(width=self.width, height=self.height)

        self.bg_color = "#3B3F51" if self.dark_theme else "#D3D7E0"
        self.active_bg_color = "#5E81AC" if self.dark_theme else "#88C0D0"
        self.fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"
        self.active_fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"

        self.config(bg=self.parent_background())

        self.current_value = values[0] if values else ""
        self.is_open = False
        self.dropdown_image = None
        self.menu_items = []

        self.bind("<Button-1>", self.toggle_dropdown)
        self.redraw()

    def parent_background(self):
        try:
            return self.master.cget("bg")
        except:
            return "#2A2D3E" if self.dark_theme else "#F5F7FA"

    def redraw(self):
        self.delete("all")
        self.config(bg=self.parent_background())

        scale = 2
        img_width = int(self.width * scale)
        img_height = int(self.height * scale)
        image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        bg_color = self.active_bg_color if self.is_open else self.bg_color
        self.create_rounded_rect(draw, 0, 0, img_width, img_height, radius=10 * scale, fill=bg_color)

        try:
            font = ImageFont.truetype("segoeui.ttf", 30 * scale // 2)
        except:
            font = None
        draw.text((img_width // 2, img_height // 2), self.current_value, fill=self.fg_color, font=font, anchor="mm")

        image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        self.dropdown_image = ImageTk.PhotoImage(image)
        self.create_image(0, 0, anchor="nw", image=self.dropdown_image)

    def create_rounded_rect(self, draw, x1, y1, x2, y2, radius, **kwargs):
        draw.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=kwargs.get("fill"), outline=None)

    def toggle_dropdown(self, event):
        if self.is_open:
            self.close_dropdown()
        else:
            self.open_dropdown()

    def open_dropdown(self):
        self.is_open = True
        self.redraw()
        self.menu_items = []
        for value in self.values:
            item = tk.Label(
                self.master,
                text=value,
                bg="#3B3F51" if self.dark_theme else "#D3D7E0",
                fg="#D8DEE9" if self.dark_theme else "#2E3440",
                font=("Segoe UI", 10),
                anchor="w",
                padx=10,
                pady=5
            )
            item.place(
                x=self.winfo_x(),
                y=self.winfo_y() + self.height + len(self.menu_items) * 30,
                width=self.width,
                height=30
            )
            item.bind("<Button-1>", lambda e, v=value: self.select_value(v))
            self.menu_items.append(item)

    def close_dropdown(self):
        self.is_open = False
        for item in self.menu_items:
            item.destroy()
        self.menu_items = []
        self.redraw()

    def select_value(self, value):
        self.current_value = value
        self.close_dropdown()
        if self.command:
            self.command()

    def get(self):
        return self.current_value

    def set(self, value):
        if value in self.values:
            self.current_value = value
            self.redraw()

    def config(self, **kwargs):
        if "dark_theme" in kwargs:
            self.dark_theme = kwargs.pop("dark_theme")
            self.bg_color = "#3B3F51" if self.dark_theme else "#D3D7E0"
            self.active_bg_color = "#5E81AC" if self.dark_theme else "#88C0D0"
            self.fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"
            self.active_fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"
            self.config(bg=self.parent_background())
            self.redraw()
        super().config(**kwargs)

class CustomSwitch(tk.Canvas):
    def __init__(self, parent, text, variable=None, command=None, **kwargs):
        self.dark_theme = kwargs.pop("dark_theme", False)
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.text = text
        self.variable = variable or tk.BooleanVar()
        self.command = command
        self.width = kwargs.get("width", 60)
        self.height = kwargs.get("height", 30)
        self.config(width=self.width, height=self.height)

        self.bg_color = "#3B3F51" if self.dark_theme else "#D3D7E0"
        self.active_bg_color = "#5E81AC" if self.dark_theme else "#88C0D0"
        self.knob_color = "#D8DEE9" if self.dark_theme else "#2E3440"

        self.config(bg=self.parent_background())

        self.switch_image = None

        self.bind("<Button-1>", self.toggle)

        self.redraw()

    def parent_background(self):
        try:
            return self.master.cget("bg")
        except:
            return "#2A2D3E" if self.dark_theme else "#F5F7FA"

    def redraw(self):
        self.delete("all")
        self.config(bg=self.parent_background())  # Обновляем фон холста

        scale = 2
        img_width = int(self.width * scale)
        img_height = int(self.height * scale)
        image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        bg_color = self.active_bg_color if self.variable.get() else self.bg_color
        self.create_rounded_rect(draw, 0, 0, img_width, img_height, radius=15 * scale, fill=bg_color)

        knob_radius = (self.height // 2 - 4) * scale
        knob_x = (self.width - self.height // 2 - 4) * scale if self.variable.get() else (self.height // 2 + 4) * scale
        knob_y = img_height // 2
        draw.ellipse(
            (knob_x - knob_radius, knob_y - knob_radius, knob_x + knob_radius, knob_y + knob_radius),
            fill=self.knob_color
        )

        try:
            font = ImageFont.truetype("segoeui.ttf", 30 * scale // 2)
        except:
            font = None
        text_x = img_width + 20 * scale
        draw.text((text_x, img_height // 2), self.text, fill=self.knob_color, font=font, anchor="lm")

        image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        self.switch_image = ImageTk.PhotoImage(image)
        self.create_image(0, 0, anchor="nw", image=self.switch_image)

    def create_rounded_rect(self, draw, x1, y1, x2, y2, radius, **kwargs):
        draw.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=kwargs.get("fill"), outline=None)

    def toggle(self, event):
        self.variable.set(not self.variable.get())
        self.redraw()
        if self.command:
            self.command()

    def config(self, **kwargs):
        if "dark_theme" in kwargs:
            self.dark_theme = kwargs.pop("dark_theme")
            self.bg_color = "#3B3F51" if self.dark_theme else "#D3D7E0"
            self.active_bg_color = "#5E81AC" if self.dark_theme else "#88C0D0"
            self.knob_color = "#D8DEE9" if self.dark_theme else "#2E3440"
            self.config(bg=self.parent_background())
            self.redraw()
        super().config(**kwargs)

class CustomEntry(tk.Canvas):
    def __init__(self, parent, textvariable=None, placeholder="", width=200, height=30, dark_theme=False, **kwargs):
        super().__init__(parent, highlightthickness=0, width=width, height=height, **kwargs)
        self.dark_theme = dark_theme
        self.textvariable = textvariable or tk.StringVar()
        self.placeholder = placeholder
        self.width = width
        self.height = height

        self.bg_color = "#3B3F51" if self.dark_theme else "#E4E7EB"
        self.text_color = "#D8DEE9" if self.dark_theme else "#2E3440"
        self.placeholder_color = "#7A7A7A"
        self.canvas_bg = self.parent_background()

        self.configure(bg=self.canvas_bg)  # <<< ЭТО ВАЖНО!

        self.entry = tk.Entry(
            self,
            textvariable=self.textvariable,
            bd=0,
            font=("Segoe UI", 10),
            relief="flat",
            bg=self.bg_color,
            fg=self.text_color,
            insertbackground=self.text_color
        )
        self.entry.place(x=10, y=5, width=self.width - 20, height=self.height - 10)

        self.bind("<Configure>", self.redraw)
        self.entry.bind("<FocusIn>", self.clear_placeholder)
        self.entry.bind("<FocusOut>", self.show_placeholder)

        self.redraw()
        self.show_placeholder()

    def parent_background(self):
        try:
            return self.master.cget("bg")
        except:
            return "#2A2D3E" if self.dark_theme else "#F5F7FA"

    def redraw(self, event=None):
        self.delete("all")
        self.configure(bg=self.canvas_bg)  # снова, для надёжности
        self.create_rounded_rect(
            0, 0, self.width, self.height, radius=10, fill=self.bg_color, outline=""
        )

    def create_rounded_rect(self, x1, y1, x2, y2, radius=10, **kwargs):
        self.create_rectangle(x1 + radius, y1, x2 - radius, y2, **kwargs)
        self.create_rectangle(x1, y1 + radius, x2, y2 - radius, **kwargs)
        self.create_arc(x1, y1, x1 + 2 * radius, y1 + 2 * radius, start=90, extent=90, style="pieslice", **kwargs)
        self.create_arc(x2 - 2 * radius, y1, x2, y1 + 2 * radius, start=0, extent=90, style="pieslice", **kwargs)
        self.create_arc(x1, y2 - 2 * radius, x1 + 2 * radius, y2, start=180, extent=90, style="pieslice", **kwargs)
        self.create_arc(x2 - 2 * radius, y2 - 2 * radius, x2, y2, start=270, extent=90, style="pieslice", **kwargs)

    def clear_placeholder(self, event=None):
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, tk.END)
            self.entry.config(fg=self.text_color)

    def show_placeholder(self, event=None):
        if not self.textvariable.get():
            self.entry.insert(0, self.placeholder)
            self.entry.config(fg=self.placeholder_color)

    def get(self):
        val = self.entry.get()
        return "" if val == self.placeholder else val

    def set(self, value):
        self.textvariable.set(value)
        self.clear_placeholder()

    def config(self, **kwargs):
        if "dark_theme" in kwargs:
            self.dark_theme = kwargs.pop("dark_theme")
            self.bg_color = "#3B3F51" if self.dark_theme else "#E4E7EB"
            self.text_color = "#D8DEE9" if self.dark_theme else "#2E3440"
            self.entry.config(
                bg=self.bg_color,
                fg=self.text_color,
                insertbackground=self.text_color
            )
            self.redraw()
        super().config(**kwargs)

class CustomHotkeyButton(tk.Canvas):
    def __init__(self, parent, text, command=None, dark_theme=False, width=100, height=30, **kwargs):
        super().__init__(parent, highlightthickness=0, width=width, height=height, **kwargs)
        self.text = text
        self.command = command
        self.dark_theme = dark_theme
        self.width = width
        self.height = height
        self.key = text  # Храним текущую клавишу

        # Цвета аналогичны CustomButton
        self.bg_color = "#3B3F51" if self.dark_theme else "#D3D7E0"
        self.active_bg_color = "#5E81AC" if self.dark_theme else "#88C0D0"
        self.fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"
        self.active_fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"

        # Устанавливаем фон один раз при инициализации
        self.configure(bg=self.parent_background())

        self.is_hovered = False
        self.is_pressed = False
        self.button_image = None
        self.animation_frames = []
        self.current_frame = 0
        self.animation_running = False

        # Привязываем события
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Configure>", self.redraw)

        self.redraw()

    def parent_background(self):
        try:
            return self.master.cget("bg")
        except:
            return "#2A2D3E" if self.dark_theme else "#F5F7FA"

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb):
        return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

    def interpolate_color(self, color1, color2, factor):
        rgb1 = self.hex_to_rgb(color1)
        rgb2 = self.hex_to_rgb(color2)
        new_rgb = tuple(int(rgb1[i] + (rgb2[i] - rgb1[i]) * factor) for i in range(3))
        return self.rgb_to_hex(new_rgb)

    def create_rounded_rect(self, draw, x1, y1, x2, y2, radius, **kwargs):
        draw.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=kwargs.get("fill"), outline=None)

    def draw_button(self, bg_color):
        scale = 2
        img_width = int(self.width * scale)
        img_height = int(self.height * scale)
        image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        fg_color = self.active_fg_color if (self.is_hovered or self.is_pressed) else self.fg_color
        self.create_rounded_rect(draw, 0, 0, img_width, img_height, radius=15 * scale, fill=bg_color)
        try:
            font = ImageFont.truetype("segoeui.ttf", 30 * scale // 2)
        except:
            font = None
        draw.text((img_width // 2, img_height // 2), self.text, fill=fg_color, font=font, anchor="mm")

        image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)

    def create_animation_frames(self, start_color, end_color, steps=10):
        self.animation_frames = []
        for i in range(steps):
            factor = i / (steps - 1) if steps > 1 else 1
            color = self.interpolate_color(start_color, end_color, factor)
            self.animation_frames.append(self.draw_button(color))

    def on_enter(self, event):
        if not self.is_hovered:
            self.is_hovered = True
            self.is_pressed = False
            self.animation_running = True
            self.current_frame = 0
            self.create_animation_frames(self.bg_color, self.active_bg_color)
            self.animate()

    def on_leave(self, event):
        if self.is_hovered:
            self.is_hovered = False
            self.is_pressed = False
            self.animation_running = True
            self.current_frame = 0
            self.create_animation_frames(self.active_bg_color, self.bg_color)
            self.animate()

    def on_press(self, event):
        self.is_pressed = True
        self.redraw()

    def on_release(self, event):
        self.is_pressed = False
        if self.is_hovered:
            self.redraw()
        else:
            self.is_hovered = False
            self.animation_running = False
            self.redraw()
        if self.command:  # Убрали проверку is_hovered
            self.command()

    def animate(self):
        if self.current_frame < len(self.animation_frames) and self.animation_running:
            self.button_image = self.animation_frames[self.current_frame]
            self.delete("all")
            self.create_image(0, 0, anchor="nw", image=self.button_image)
            self.current_frame += 1
            self.after(30, self.animate)
        else:
            self.animation_running = False
            self.redraw()

    def redraw(self, event=None):
        self.delete("all")
        bg_color = self.active_bg_color if (self.is_hovered or self.is_pressed) else self.bg_color
        self.button_image = self.draw_button(bg_color)
        self.create_image(0, 0, anchor="nw", image=self.button_image)

    def set_key(self, key):
        """Обновить отображаемую клавишу."""
        self.key = key
        self.text = key
        self.redraw()

    def config(self, **kwargs):
        """Обновить конфигурацию кнопки."""
        needs_redraw = False
        if "dark_theme" in kwargs:
            self.dark_theme = kwargs.pop("dark_theme")
            self.bg_color = "#3B3F51" if self.dark_theme else "#D3D7E0"
            self.active_bg_color = "#5E81AC" if self.dark_theme else "#88C0D0"
            self.fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"
            self.active_fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"
            self.configure(bg=self.parent_background())
            needs_redraw = True
        if "text" in kwargs:
            self.key = kwargs.pop("text")
            self.text = self.key
            needs_redraw = True
        super().config(**kwargs)
        if needs_redraw:
            self.redraw()

class CustomListBox(tk.Frame):
    def __init__(self, parent, height=130, dark_theme=False, width=300, **kwargs):
        super().__init__(parent, **kwargs)
        self.dark_theme = dark_theme
        self.width = width

        self.bg_color = "#2A2D3E" if self.dark_theme else "#F5F7FA"
        self.canvas_bg = "#2A2D3E" if self.dark_theme else "#F5F7FA"
        self.fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"
        self.select_color = "#5E81AC" if self.dark_theme else "#1E90FF"
        self.border_color = "#3B3F51" if self.dark_theme else "#E4E7EB"

        self.canvas = tk.Canvas(self, highlightthickness=0, bg=self.canvas_bg)
        self.canvas.pack(side="left", fill="y")

        # Создание listbox внутри canvas с увеличенными отступами
        self.listbox = tk.Listbox(
            self.canvas,
            width=width,
            bg=self.bg_color,
            fg=self.fg_color,
            selectbackground=self.select_color,
            selectforeground=self.fg_color,
            highlightthickness=0,
            bd=0,
            activestyle="none",
            exportselection=False,
            font=("Segoe UI", 12)
        )

        self.listbox_id = self.canvas.create_window(
            (15, 15),  # Увеличиваем отступы с 10 до 15, чтобы дать больше места
            window=self.listbox,
            anchor="nw",
            width=width - 30  # Уменьшаем ширину Listbox, чтобы учесть новые отступы
        )

        self.image = None
        self.redraw()

        # Обновляем высоту при изменении содержимого
        self.listbox.bind("<Configure>", self.update_canvas)

    def update_canvas(self, event=None):
        try:
            self.canvas.itemconfig(self.listbox_id, width=self.width - 30)  # Учитываем новые отступы
            item_height = 30  # Высота одного элемента
            total_items = self.listbox.size()
            total_height = total_items * item_height + 30  # Добавляем отступы сверху и снизу

            # Устанавливаем высоту listbox равной количеству элементов
            self.listbox.config(height=total_items)
            # Устанавливаем высоту canvas равной высоте содержимого
            self.canvas.config(height=total_height)

        except tk.TclError as e:
            print(f"Error in update_canvas: {e}")
        self.redraw()

    def redraw(self):
        self.canvas.delete("border")
        scale = 2
        img_width = int(self.width * scale)
        item_count = self.listbox.size()
        # Учитываем отступы сверху и снизу (15 + 15 = 30)
        img_height = int(max(1, item_count) * 30 * scale + 30 * scale)

        image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Увеличиваем отступы для рамки, чтобы она не перекрывала текст
        draw.rounded_rectangle(
            [(15 * scale, 15 * scale), (img_width - 15 * scale, img_height - 15 * scale)],
            radius=10 * scale,
            outline=self.border_color,
            width=2 * scale
        )

        # Масштабируем изображение с учетом новых размеров
        image = image.resize((self.width, max(1, item_count) * 30 + 30), Image.Resampling.LANCZOS)
        self.image = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, anchor="nw", image=self.image, tags="border")

    def config(self, **kwargs):
        if "dark_theme" in kwargs:
            self.dark_theme = kwargs.pop("dark_theme")
            self.bg_color = "#2A2D3E" if self.dark_theme else "#F5F7FA"
            self.canvas_bg = "#2A2D3E" if self.dark_theme else "#F5F7FA"
            self.fg_color = "#D8DEE9" if self.dark_theme else "#2E3440"
            self.select_color = "#5E81AC" if self.dark_theme else "#1E90FF"
            self.border_color = "#3B3F51" if self.dark_theme else "#E4E7EB"
            self.canvas.config(bg=self.canvas_bg)
            self.listbox.config(
                bg=self.bg_color,
                fg=self.fg_color,
                selectbackground=self.select_color,
                selectforeground=self.fg_color
            )
            self.redraw()
        if kwargs:
            super().config(**kwargs)

    def configure(self, **kwargs):
        self.config(**kwargs)

    def insert(self, *args, **kwargs):
        self.listbox.insert(*args, **kwargs)
        self.update_canvas()

    def delete(self, *args, **kwargs):
        self.listbox.delete(*args, **kwargs)
        self.update_canvas()

    def size(self):
        return self.listbox.size()

    def get(self, *args, **kwargs):
        return self.listbox.get(*args, **kwargs)

    def bind(self, *args, **kwargs):
        self.listbox.bind(*args, **kwargs)

    def curselection(self):
        return self.listbox.curselection()

    def nearest(self, y):
        return self.listbox.nearest(y)

    def selection_clear(self, *args, **kwargs):
        self.listbox.selection_clear(*args, **kwargs)

    def selection_set(self, *args, **kwargs):
        self.listbox.selection_set(*args, **kwargs)

    def drop_target_register(self, *args, **kwargs):
        try:
            self.listbox.drop_target_register(*args, **kwargs)
        except AttributeError as e:
            print(f"Error in drop_target_register: {e}")

    def dnd_bind(self, *args, **kwargs):
        try:
            self.listbox.dnd_bind(*args, **kwargs)
        except AttributeError as e:
            print(f"Error in dnd_bind: {e}")


