# src/listeners/selection_listener.py
import logging
import threading
import queue
from pynput import mouse
from typing import Callable, Dict, Any
from src.capture.text_selection import get_selected_text

class SelectionListener:
    """
    监听全局鼠标划词动作。
    采用生产者-消费者模型，将pynput的事件回调与耗时的UIA操作解耦，
    以解决 [WinError -2147417843] 线程冲突问题。
    """
    def __init__(self, callback: Callable[[Dict[str, Any]], None]):
        self.callback = callback
        self._last_text = ""
        # 创建一个线程安全的队列，用于在监听线程和工作线程之间传递任务
        self.task_queue = queue.Queue()

    def _selection_worker(self):
        """
        这是一个在独立线程中运行的工作函数。
        它会持续等待任务，并安全地执行划词捕获逻辑。
        """
        while True:
            try:
                # 阻塞式等待，直到队列中有任务
                _ = self.task_queue.get()
                
                selection_data = get_selected_text()
                
                if selection_data and selection_data['data'] != self._last_text:
                    self._last_text = selection_data['data']
                    self.callback(selection_data)

            except Exception as e:
                logging.error(f"划词工作线程发生错误: {e}", exc_info=True)
            finally:
                # 标记任务完成
                self.task_queue.task_done()

    def _on_click(self, x, y, button, pressed):
        """
        pynput 鼠标点击事件的回调函数。
        这个函数现在非常轻量，只负责向队列中添加一个任务。
        """
        if button == mouse.Button.left and not pressed:
            # 放入一个简单的信号，通知工作线程开始工作
            if self.task_queue.empty(): # 防止队列中任务积压
                self.task_queue.put("GET_SELECTION")

    def run(self):
        """
        启动鼠标监听器和划词工作线程。
        """
        # 启动在后台运行的划词工作线程
        worker_thread = threading.Thread(target=self._selection_worker, name="SelectionWorkerThread", daemon=True)
        worker_thread.start()

        logging.info("划词监听器正在运行...")
        with mouse.Listener(on_click=self._on_click) as listener:
            listener.join()

