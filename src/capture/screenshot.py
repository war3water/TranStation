# src/capture/screenshot.py
import tkinter as tk
from mss import mss
from PIL import Image, ImageTk
import base64
from io import BytesIO
from datetime import datetime
import logging
import time
import sys

# 尝试为Windows的“复制到剪贴板”功能导入必要的库
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    try:
        import win32clipboard
        import win32con
    except ImportError:
        logging.warning("pywin32 未安装, “复制到剪贴板”功能将不可用。")
        IS_WINDOWS = False

class ModernScreenshot:
    """
    一个现代化的截图工具，具有跨屏智能定位、可拖动预览、缩放和复制功能。
    """
    def __init__(self, root: tk.Tk, config: dict, ipc_queue: callable):
        self.root = root
        self.config = config.get('screenshot', {})
        self.ipc_queue = ipc_queue
        
        self.overlay = None
        self.canvas = None
        self.start_x, self.start_y = None, None
        self.end_x, self.end_y = None, None
        self.rect = None

        self._captured_data = None
        self._captured_image = None # 存储原始Pillow图像
        
        self._drag_start_x = 0
        self._drag_start_y = 0
        
        # 缩放相关属性
        self._zoom_level = 1.0
        self._zoom_step = 0.1
        self._min_zoom, self._max_zoom = 0.1, 5.0
        self._zoom_label = None
        self._image_label = None # 对图片标签的引用
        self._tk_image = None # 对PhotoImage的引用，防止被垃圾回收

        with mss() as sct:
            self.monitors = sct.monitors

    def _get_virtual_screen_geometry(self):
        return self.monitors[0] if self.monitors else {'left': 0, 'top': 0, 'width': 0, 'height': 0}

    def _setup_overlay(self):
        geometry = self._get_virtual_screen_geometry()
        self.overlay = tk.Toplevel(self.root)
        self.overlay.overrideredirect(True)
        self.overlay.attributes('-alpha', self.config.get('overlay_alpha', 0.3))
        self.overlay.attributes('-topmost', True)
        self.overlay.geometry(f"{geometry['width']}x{geometry['height']}+{geometry['left']}+{geometry['top']}")

        self.canvas = tk.Canvas(self.overlay, cursor="cross", bg="black")
        self.canvas.pack(fill="both", expand=True)
        
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_press)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_release)
        self.overlay.bind("<Escape>", lambda e: self._exit_process())
        
        self.screen_geometry = geometry

    def _on_mouse_press(self, event):
        self.start_x, self.start_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if not self.rect:
            self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y,
                outline=self.config.get('border_color', 'red'), width=self.config.get('border_width', 2))

    def _on_mouse_drag(self, event):
        self.end_x, self.end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, self.end_x, self.end_y)

    def _on_mouse_release(self, event):
        self.overlay.destroy()
        if self.end_x is None: self._exit_process(); return
        x1, y1 = min(self.start_x, self.end_x), min(self.start_y, self.end_y)
        x2, y2 = max(self.start_x, self.end_x), max(self.start_y, self.end_y)
        width, height = x2 - x1, y2 - y1

        if width > 10 and height > 10:
            screen_x, screen_y = self.screen_geometry['left'] + x1, self.screen_geometry['top'] + y1
            self._capture_and_preview(int(screen_x), int(screen_y), int(width), int(height))
        else:
            self._exit_process()

    def _capture_and_preview(self, x, y, width, height):
        with mss() as sct:
            monitor = {"top": y, "left": x, "width": width, "height": height}
            sct_img = sct.grab(monitor)
            self._captured_image = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        buffered = BytesIO()
        self._captured_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        self._captured_data = {"type": "image", "timestamp": datetime.utcnow().isoformat() + "Z", "data": img_str,
                               "metadata": {"format": "png", "encoding": "base64", "region": {"x": x, "y": y, "width": width, "height": height}}}
        self._create_stylish_preview(x, y, width, height)

    def _create_stylish_preview(self, sel_x, sel_y, sel_w, sel_h):
        preview = tk.Toplevel(self.root)
        preview.overrideredirect(True)
        preview.attributes('-topmost', True)
        BG_COLOR = self.config.get('preview_bg', '#2e2e2e')
        preview.config(bg=BG_COLOR, bd=2, relief="solid", highlightcolor=BG_COLOR, highlightbackground=BG_COLOR)
        
        self._image_label = tk.Label(preview, bd=0)
        self._image_label.pack(padx=2, pady=2)
        
        self._zoom_label = tk.Label(self._image_label, text="100%", bg="black", fg="white", padx=5, pady=2, font=("Segoe UI", 8))
        
        self._update_image_zoom(preview, initial=True)

        self._add_buttons(preview)
        self._make_draggable(preview)
        self._add_context_menu(preview)
        
        self._position_preview_window(preview, sel_x, sel_y, sel_w, sel_h)
        preview.focus_force()
        preview.protocol("WM_DELETE_WINDOW", lambda: self._close_preview(preview))
        
        # 绑定滚轮事件
        preview.bind_all("<MouseWheel>", lambda e: self._on_mouse_wheel(e, preview))

    def _on_mouse_wheel(self, event, window):
        """处理鼠标滚轮事件以进行缩放。"""
        if event.delta > 0:
            self._zoom_level += self._zoom_step
        else:
            self._zoom_level -= self._zoom_step
        self._zoom_level = max(self._min_zoom, min(self._max_zoom, self._zoom_level))
        self._update_image_zoom(window)

    def _update_image_zoom(self, window, initial=False):
        """根据当前缩放级别更新图片和窗口大小。"""
        new_width = int(self._captured_image.width * self._zoom_level)
        new_height = int(self._captured_image.height * self._zoom_level)
        
        if new_width < 1 or new_height < 1: return

        resized_image = self._captured_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self._tk_image = ImageTk.PhotoImage(resized_image)
        self._image_label.config(image=self._tk_image)
        
        # 更新缩放标签
        self._zoom_label.config(text=f"{int(self._zoom_level * 100)}%")
        self._zoom_label.place(relx=1.0, rely=1.0, anchor='se', x=-5, y=-5)
        
        if not initial:
            self._reposition_after_zoom(window)
            
    def _reposition_after_zoom(self, window):
        """缩放后重新定位窗口，使其中心保持不变。"""
        window.update_idletasks()
        center_x = window.winfo_x() + window.winfo_width() // 2
        center_y = window.winfo_y() + window.winfo_height() // 2
        
        new_win_w = window.winfo_width()
        new_win_h = window.winfo_height()
        
        new_x = center_x - new_win_w // 2
        new_y = center_y - new_win_h // 2
        
        window.geometry(f"+{new_x}+{new_y}")
        
    def _copy_image_to_clipboard(self, window):
        """将Pillow图像复制到Windows剪贴板。"""
        if not IS_WINDOWS:
            logging.warning("“复制图片”功能仅在Windows上受支持。")
            return

        output = BytesIO()
        # 将图像转换为 DIB 格式需要先转为 RGB
        self._captured_image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:] # DIB format is BMP without the header
        output.close()

        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_DIB, data)
            win32clipboard.CloseClipboard()
            self._show_copy_feedback(window)
        except Exception as e:
            logging.error(f"复制到剪贴板失败: {e}")
            if 'OpenClipboard' in str(e): # 尝试处理剪贴板被占用的情况
                try: win32clipboard.CloseClipboard()
                except: pass

    def _show_copy_feedback(self, window):
        """在窗口中央短暂显示“已复制!”提示。"""
        feedback = tk.Label(window, text="已复制!", bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"), padx=15, pady=8)
        feedback.place(relx=0.5, rely=0.5, anchor='center')
        window.after(1000, feedback.destroy)
        
    def _add_context_menu(self, window):
        """为右键菜单添加“复制”和“关闭”选项。"""
        BG, FG, ACTIVE_BG = self.config.get('preview_bg', '#2e2e2e'), self.config.get('preview_button_fg', '#ffffff'), self.config.get('preview_button_active_bg', '#5a5a5a')
        
        menu = tk.Menu(window, tearoff=0, bg=BG, fg=FG, activebackground=ACTIVE_BG, activeforeground=FG, relief='flat')
        
        if IS_WINDOWS:
            copy_command = lambda: (menu.unpost(), self._copy_image_to_clipboard(window))
            menu.add_command(label="复制图片 (Copy)", command=copy_command)
            menu.add_separator()
        
        close_command = lambda: (menu.unpost(), self._fade_out_and_close(window))
        menu.add_command(label="关闭 (Close)", command=close_command)
        
        def show_menu(event):
            menu.post(event.x_root, event.y_root)

        window.bind("<Button-3>", show_menu)

    # --- 以下方法与上一版本基本相同，为保持完整性而包含 ---

    def _add_buttons(self, preview):
        BG_COLOR, BTN_BG, BTN_FG, BTN_ACTIVE_BG = self.config.get('preview_bg', '#2e2e2e'), self.config.get('preview_button_bg', '#4a4a4a'), self.config.get('preview_button_fg', '#ffffff'), self.config.get('preview_button_active_bg', '#5a5a5a')
        button_frame = tk.Frame(preview, bg=BG_COLOR)
        button_frame.pack(fill='x', padx=10, pady=(5, 10))
        def create_button(parent, text, command):
            return tk.Button(parent, text=text, command=command, bg=BTN_BG, fg=BTN_FG, activebackground=BTN_ACTIVE_BG, activeforeground=BTN_FG, relief='flat', padx=12, pady=5, font=("Segoe UI", 9, "bold"), cursor="hand2")
        confirm_button = create_button(button_frame, "确 认", lambda: self._confirm_and_send(preview))
        cancel_button = create_button(button_frame, "取 消", lambda: self._close_preview(preview))
        button_frame.columnconfigure((0, 1), weight=1)
        cancel_button.grid(row=0, column=0, sticky='ew', padx=(0, 5))
        confirm_button.grid(row=0, column=1, sticky='ew', padx=(5, 0))
        preview.bind("<Escape>", lambda e: self._close_preview(preview))

    def _find_target_monitor(self, x, y):
        for monitor in self.monitors[1:]:
            if monitor['left'] <= x < monitor['left'] + monitor['width'] and monitor['top'] <= y < monitor['top'] + monitor['height']:
                return monitor
        return self.monitors[1] if len(self.monitors) > 1 else self.monitors[0]

    def _position_preview_window(self, window, sel_x, sel_y, sel_w, sel_h):
        window.update_idletasks()
        win_w, win_h = window.winfo_width(), window.winfo_height()
        center_x, center_y = sel_x + sel_w // 2, sel_y + sel_h // 2
        target_monitor = self._find_target_monitor(center_x, center_y)
        ideal_x, ideal_y = center_x - win_w // 2, center_y - win_h // 2
        mon_x1, mon_y1 = target_monitor['left'], target_monitor['top']
        mon_x2, mon_y2 = mon_x1 + target_monitor['width'], mon_y1 + target_monitor['height']
        final_x = max(mon_x1, min(ideal_x, mon_x2 - win_w))
        final_y = max(mon_y1, min(ideal_y, mon_y2 - win_h))
        window.geometry(f'{win_w}x{win_h}+{final_x}+{final_y}')

    def _make_draggable(self, window):
        self._image_label.bind("<ButtonPress-1>", self._on_drag_start)
        self._image_label.bind("<B1-Motion>", self._on_drag_motion)

    def _fade_out_and_close(self, window):
        alpha = 1.0
        while alpha > 0.0:
            alpha -= 0.1
            if alpha < 0.0: alpha = 0.0
            try:
                window.attributes('-alpha', alpha)
                window.update()
            except tk.TclError: break
            time.sleep(0.02)
        self._close_preview(window)

    def _on_drag_start(self, event):
        self._drag_start_x, self._drag_start_y = event.x, event.y

    def _on_drag_motion(self, event):
        window = event.widget.winfo_toplevel()
        x, y = window.winfo_x() - self._drag_start_x + event.x, window.winfo_y() - self._drag_start_y + event.y
        window.geometry(f"+{x}+{y}")
        
    def _confirm_and_send(self, window: tk.Toplevel):
        if self.ipc_queue and self._captured_data: self.ipc_queue.put(self._captured_data)
        self._close_preview(window)

    def _close_preview(self, window: tk.Toplevel):
        if window.winfo_exists(): window.destroy()
        self._exit_process()
        
    def _exit_process(self):
        if self.root.winfo_exists(): self.root.quit()

    def start(self):
        self._setup_overlay()

def take_screenshot_multiprocess(config: dict, ipc_queue: callable):
    try:
        root = tk.Tk()
        root.withdraw()
        app = ModernScreenshot(root, config, ipc_queue)
        app.start()
        root.mainloop()
    except Exception as e:
        logging.error(f"截图进程内部发生错误: {e}", exc_info=True)

