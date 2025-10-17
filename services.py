import threading
import logging
import time
from concurrent.futures import ThreadPoolExecutor

# 这是一个假设的 worker 函数，你的实际代码会更复杂
def selection_worker_task(text):
    """处理选中文本的工作函数。"""
    logging.info(f"工作线程开始处理文本: '{text[:30]}...'")
    # 这里模拟了与 COM 组件交互等耗时操作
    # 在实际代码中，这里是调用 get_selected_text 的地方
    time.sleep(1) 
    logging.debug(f"文本处理完毕。")


class StoppableThread(threading.Thread):
    """一个可停止线程的基类，包含通用逻辑。"""
    def __init__(self, config, shutdown_event, name=None):
        super().__init__(name=name)
        self.config = config
        self.shutdown_event = shutdown_event
        self.logger = logging.getLogger(self.__class__.__name__)


class SelectionListenerThread(StoppableThread):
    """
    监听划词选择的线程。
    这个类现在会优雅地关闭其内部的线程池。
    """
    def __init__(self, config, shutdown_event):
        super().__init__(config, shutdown_event, name="SelectionListenerThread")
        # 初始化一个线程池来处理划词任务
        self.executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix='SelectionWorker')
        self.last_text = None

    def run(self):
        self.logger.info("划词监听器正在运行...")
        
        # 线程的主循环，会定期检查 shutdown_event
        while not self.shutdown_event.is_set():
            try:
                # 你的划词逻辑应该放在这里。
                # 例如: selected_text = get_selected_text_with_timeout()
                # 这里我们用一个模拟的文本来演示
                selected_text = f"这是在 {time.time()} 获取的模拟文本" # 替换为你的真实划词函数

                if selected_text and selected_text != self.last_text:
                    self.last_text = selected_text
                    # 提交任务到线程池
                    if not self.executor._shutdown:
                        self.executor.submit(selection_worker_task, selected_text)
                
                # 等待一小段时间再检查，避免 CPU 占用过高
                # 这个等待也使得关闭信号能被更快地响应
                self.shutdown_event.wait(timeout=0.2)

            except Exception as e:
                self.logger.error(f"划词监听循环发生错误: {e}", exc_info=True)

        self.logger.info("监听到关闭信号，正在清理...")
        # 【关键】在线程退出前，显式并优雅地关闭线程池
        # wait=True 会等待所有已提交的任务完成
        self.executor.shutdown(wait=True)
        self.logger.info("划词监听器已停止。")


class HotkeyListenerThread(StoppableThread):
    """快捷键监听线程（示例）。"""
    def __init__(self, config, shutdown_event):
        super().__init__(config, shutdown_event, name="HotkeyListenerThread")

    def run(self):
        # 你的快捷键监听逻辑，例如 pynput.keyboard.Listener
        # 监听器的主循环也应该通过检查 self.shutdown_event.is_set() 来退出
        self.logger.info("快捷键监听器正在运行...")
        while not self.shutdown_event.is_set():
            # 模拟阻塞的监听操作
            self.shutdown_event.wait(timeout=0.2)
        self.logger.info("快捷键监听器已停止。")


class WebSocketServerThread(StoppableThread):
    """WebSocket 服务器线程（示例）。"""
    def __init__(self, config, shutdown_event):
        super().__init__(config, shutdown_event, name="WebSocketServerThread")

    def run(self):
        # 你的 WebSocket 服务器启动和运行逻辑
        # 服务器的 accept() 或 serve_forever() 循环需要被修改为可超时的，
        # 以便能检查 self.shutdown_event.is_set()
        self.logger.info("WebSocket 服务器正在运行...")
        while not self.shutdown_event.is_set():
             # 模拟服务器的阻塞操作
            self.shutdown_event.wait(timeout=0.2)
        self.logger.info("WebSocket 服务器已停止。")
