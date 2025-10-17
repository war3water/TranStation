# src/capture/screenshot.py
import tkinter as tk
from mss import mss
from PIL import Image, ImageTk
import base64
from io import BytesIO
from datetime import datetime
import logging

class Screenshot:
    """
    一个用于创建全屏截图蒙版并允许用户选择区域的类。
    """
    def __init__(self, config: dict, callback: callable):
        self.config = config
        self.callback = callback
        self.root = None
        self.canvas = None
        self.start_x = None
        self.start_y = None
        self.rect = None

    def _get_virtual_screen_geometry(self):
        """计算能够覆盖所有显示器的虚拟屏幕的边界。"""
        with mss() as sct:
            monitors = sct.monitors[1:]  # 忽略第一个聚合监视器
            if not monitors: # 单显示器情况
                 monitors = [sct.monitors[0]]

            min_x = min(m['left'] for m in monitors)
            min_y = min(m['top'] for m in monitors)
            max_x = max(m['left'] + m['width'] for m in monitors)
            max_y = max(m['top'] + m['height'] for m in monitors)
            
            width = max_x - min_x
            height = max_y - min_y
            
            return {'left': min_x, 'top': min_y, 'width': width, 'height': height}

    def _on_mouse_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if not self.rect:
            self.rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, self.start_x, self.start_y,
                outline=self.config['screenshot']['border_color'],
                width=self.config['screenshot']['border_width']
            )

    def _on_mouse_drag(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def _on_mouse_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)

        # 确保坐标是左上角到右下角
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        width = x2 - x1
        height = y2 - y1

        # 销毁截图窗口
        self.root.destroy()
        
        # 确保选区有效
        if width > 0 and height > 0:
            # 将窗口坐标转换为屏幕坐标
            screen_x = self.screen_geometry['left'] + x1
            screen_y = self.screen_geometry['top'] + y1
            
            self._capture_and_callback(int(screen_x), int(screen_y), int(width), int(height))

    def _capture_and_callback(self, x, y, width, height):
        """根据最终坐标进行截图并调用回调函数"""
        with mss() as sct:
            monitor = {"top": y, "left": x, "width": width, "height": height}
            sct_img = sct.grab(monitor)
            
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            data = {
                "type": "image",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": img_str,
                "metadata": {
                    "format": "png",
                    "encoding": "base64",
                    "region": {
                        "x": x,
                        "y": y,
                        "width": width,
                        "height": height
                    }
                }
            }
            if self.callback:
                self.callback(data)

    def run(self):
        """启动截图界面。"""
        self.screen_geometry = self._get_virtual_screen_geometry()
        
        self.root = tk.Tk()
        self.root.overrideredirect(True) # 移除窗口边框
        self.root.attributes('-alpha', self.config['screenshot']['overlay_alpha'])
        self.root.attributes('-topmost', True)
        self.root.geometry(f"{self.screen_geometry['width']}x{self.screen_geometry['height']}+{self.screen_geometry['left']}+{self.screen_geometry['top']}")

        self.canvas = tk.Canvas(self.root, cursor="cross", bg="black")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self._on_mouse_press)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_release)

        self.root.mainloop()

# --- 关键修复：添加此函数作为多进程的入口点 ---
def take_screenshot_multiprocess(config: dict, callback: callable):
    """
    这是一个独立的顶层函数，用于在新的进程中安全地实例化并运行截图GUI。
    """
    try:
        screenshot_app = Screenshot(config, callback)
        screenshot_app.run()
    except Exception as e:
        logging.error(f"截图进程内部发生错误: {e}", exc_info=True)

