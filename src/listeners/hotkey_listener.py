# src/listeners/hotkey_listener.py
import logging
import multiprocessing
import threading
from pynput import keyboard
from src.capture.screenshot import take_screenshot_multiprocess
from src.ipc_queue import queue as ipc_queue

class HotkeyListener:
    """
    监听全局快捷键，并支持优雅地停止。
    """
    def __init__(self, config: dict, shutdown_event: threading.Event):
        self.config = config
        self.shutdown_event = shutdown_event
        self.screenshot_process = None

    def _on_screenshot(self):
        """截图快捷键被触发时的回调函数。"""
        # 防止重复启动截图进程
        if self.screenshot_process and self.screenshot_process.is_alive():
            logging.warning("截图进程已在运行中，请勿重复触发。")
            return
            
        logging.info("截图快捷键已被触发，正在启动截图进程...")
        try:
            self.screenshot_process = multiprocessing.Process(
                target=take_screenshot_multiprocess,
                args=(self.config, ipc_queue)
            )
            self.screenshot_process.start()
        except Exception as e:
            logging.error(f"启动截图进程时发生错误: {e}", exc_info=True)

    def run(self):
        """启动快捷键监听器，并等待关闭信号。"""
        hotkey_str = self.config['hotkey']['screenshot']
        hotkeys = {hotkey_str: self._on_screenshot}

        listener = keyboard.GlobalHotKeys(hotkeys)
        listener.start()
        
        logging.info(f"正在注册快捷键: {hotkey_str}")
        logging.info("快捷键监听器正在运行...")
        
        # 等待主线程发出关闭信号
        self.shutdown_event.wait()
        
        # 停止监听
        listener.stop()
        logging.info("快捷键监听器已停止。")

