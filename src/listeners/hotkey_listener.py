# src/listeners/hotkey_listener.py
import logging
from pynput import keyboard
from src.capture.screenshot import take_screenshot_multiprocess
import multiprocessing

class HotkeyListener:
    """
    监听全局快捷键。
    """
    def __init__(self, config: dict, callback: callable):
        self.config = config
        self.callback = callback

    def _on_screenshot(self):
        """
        截图快捷键被触发时的回调函数。
        """
        logging.info("截图快捷键已被触发，正在启动截图进程...")
        try:
            # 使用多进程启动截图，以避免GUI在主线程中造成问题
            proc = multiprocessing.Process(
                target=take_screenshot_multiprocess,
                args=(self.config, self.callback)
            )
            proc.start()
        except Exception as e:
            logging.error(f"启动截图进程时发生错误: {e}", exc_info=True)

    def run(self):
        """
        启动快捷键监听器。
        """
        hotkey_str = self.config['hotkey']['screenshot']
        
        # 关键修复：直接使用快捷键字符串作为字典的键
        hotkeys = {
            hotkey_str: self._on_screenshot
        }

        logging.info(f"正在注册快捷键: {hotkey_str}")
        logging.info("快捷键监听器正在运行...")
        
        # 使用 pynput 推荐的 GlobalHotKeys 监听器，它专为处理快捷键组合而设计
        with keyboard.GlobalHotKeys(hotkeys) as listener:
            listener.join()

