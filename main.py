import threading
import time
import logging
from logging_config import setup_logging
from config_loader import load_config
from services import HotkeyListenerThread, SelectionListenerThread, WebSocketServerThread

# 创建一个全局事件，用于通知所有线程终止
shutdown_event = threading.Event()

def main():
    """
    主函数，负责初始化和管理所有服务。
    """
    try:
        setup_logging()
        config = load_config()

        logging.info("服务启动中...")
        
        # 创建所有服务线程实例，并传入关闭事件
        # (请根据你的实际服务类进行调整)
        services = [
            HotkeyListenerThread(config, shutdown_event),
            SelectionListenerThread(config, shutdown_event),
            WebSocketServerThread(config, shutdown_event)
        ]

        # 启动所有服务
        for service in services:
            service.start()

        logging.info("所有服务已成功启动。程序正在运行...")
        logging.info(f"截图快捷键: {config['hotkey']['screenshot']}")
        logging.info("划词读取功能已激活。")
        logging.info("按 Ctrl+C 退出程序。")

        # 主线程等待，直到 shutdown_event 被设置
        # 这样可以避免使用 time.sleep() 的忙等待
        shutdown_event.wait()

    except KeyboardInterrupt:
        logging.info("接收到退出信号 (Ctrl+C)，正在关闭服务...")
    except Exception as e:
        logging.critical(f"程序启动时发生致命错误: {e}", exc_info=True)
    finally:
        # 确保即使发生其他错误，也能触发关闭流程
        if not shutdown_event.is_set():
            shutdown_event.set()

        logging.info("正在等待所有服务线程停止...")
        
        # 等待所有线程完成它们的清理工作并退出
        # 将主线程放在最后 join，以防它提前退出
        main_thread = threading.current_thread()
        for t in threading.enumerate():
            if t is main_thread:
                continue
            # 给每个线程一个超时时间，防止无限期等待
            t.join(timeout=5.0) 
        
        logging.info("服务已关闭。")

if __name__ == "__main__":
    main()
