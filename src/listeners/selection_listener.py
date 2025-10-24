# src/listeners/selection_listener.py
import logging
import threading
import queue
import math
from pynput import mouse
from typing import Callable, Dict, Any, Tuple, Optional
from src.capture.text_selection import get_selected_text

class SelectionListener:
    """
    监听全局鼠标划词动作，并支持优雅地停止。
    """
    def __init__(self, callback: Callable[[Dict[str, Any]], None], shutdown_event: threading.Event):
        self.callback = callback
        self.shutdown_event = shutdown_event
        self._last_text = ""
        self.task_queue = queue.Queue()
        self._press_pos: Optional[Tuple[int, int]] = None
        self.MIN_DRAG_DISTANCE = 10

    def _selection_worker(self):
        """在独立线程中运行的工作函数，安全地执行划词捕获。"""
        while not self.shutdown_event.is_set():
            try:
                # 使用超时get，使其能够周期性地检查关闭信号
                task = self.task_queue.get(timeout=1.0)
                if task is None: # 显式哨兵值，用于快速退出
                    break
                
                selection_data = get_selected_text()
                
                if selection_data and selection_data.get('data', '').strip():
                    current_text = selection_data['data']
                    if current_text != self._last_text:
                        self._last_text = current_text
                        self.callback(selection_data)
                    else:
                        logging.debug("捕获到与上次相同的文本，已忽略。")
                else:
                    self._last_text = ""
                
                # --- 关键修复：仅在成功获取并处理任务后调用 task_done ---
                self.task_queue.task_done()

            except queue.Empty:
                continue # 超时是正常现象，继续循环检查关闭信号
            except Exception as e:
                logging.error(f"划词工作线程发生错误: {e}", exc_info=True)
        
        logging.info("划词工作线程已停止。")

    def _on_click(self, x, y, button, pressed):
        """pynput 鼠标事件回调。"""
        if button == mouse.Button.left:
            if pressed:
                self._press_pos = (x, y)
            else:
                if self._press_pos:
                    dist = math.sqrt((x - self._press_pos[0])**2 + (y - self._press_pos[1])**2)
                    if dist > self.MIN_DRAG_DISTANCE:
                        logging.debug(f"检测到有效划词动作 (拖拽距离: {dist:.2f}px)，即将捕获文本。")
                        if self.task_queue.empty():
                            self.task_queue.put("GET_SELECTION")
                    else:
                        logging.debug(f"检测到单击动作 (拖拽距离: {dist:.2f}px)，已忽略。")
                    self._press_pos = None

    def run(self):
        """启动鼠标监听器和工作线程，并等待关闭信号。"""
        worker_thread = threading.Thread(target=self._selection_worker, name="SelectionWorkerThread", daemon=True)
        worker_thread.start()

        listener = mouse.Listener(on_click=self._on_click)
        listener.start()

        logging.info("划词监听器正在运行...")
        
        # 等待主线程发出关闭信号
        self.shutdown_event.wait()

        # 停止监听器和工作线程
        listener.stop()
        self.task_queue.put(None) # 发送哨兵值以停止工作线程
        worker_thread.join(timeout=2.0) # 等待工作线程退出

        logging.info("划词监听器已停止。")

