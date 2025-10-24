# main.py
import threading
import logging
import multiprocessing
import queue
import time
from src.config_loader import ConfigLoader
from src.listeners.hotkey_listener import HotkeyListener
from src.listeners.selection_listener import SelectionListener
from src.server.websocket_server import WebSocketServer
from src.logging_config import setup_logging
from src.ipc_queue import queue as ipc_queue

def queue_bridge(ws_server: WebSocketServer, shutdown_event: threading.Event):
    """
    一个桥接函数，负责从多进程队列(ipc_queue)中获取截图数据，
    并将其放入WebSocket服务器的内部队列中。
    """
    logging.info("IPC队列桥接线程已启动，等待截图数据...")
    while not shutdown_event.is_set():
        try:
            data = ipc_queue.get(timeout=1.0)
            logging.info(f"截图数据已从IPC队列接收 (类型: {data.get('type')})，准备推送到WebSocket。")
            ws_server.queue_message(data)
        except queue.Empty:
            continue
        except Exception as e:
            logging.error(f"队列桥接线程发生错误: {e}", exc_info=True)
    logging.info("IPC队列桥接线程已关闭。")

def main():
    """
    主函数，负责初始化和管理所有服务。
    """
    multiprocessing.freeze_support()
    shutdown_event = threading.Event()

    try:
        setup_logging()
        config_loader = ConfigLoader()
        config = config_loader.get_config()

        logging.info("服务启动中...")

        ws_server = WebSocketServer(
            host=config['server']['host'],
            port=config['server']['port']
        )
        
        # --- 关键修复：将shutdown_event传递给监听器 ---
        selection_listener = SelectionListener(ws_server.queue_message, shutdown_event)
        hotkey_listener = HotkeyListener(config, shutdown_event)

        threads = [
            threading.Thread(target=ws_server.run, name="WebSocketThread", daemon=True),
            threading.Thread(target=hotkey_listener.run, name="HotkeyListenerThread"),
            threading.Thread(target=selection_listener.run, name="SelectionListenerThread"),
            threading.Thread(target=queue_bridge, args=(ws_server, shutdown_event), name="IPCBridgeThread")
        ]

        for thread in threads:
            thread.start()

        logging.info("所有服务已成功启动。程序正在运行...")
        logging.info(f"截图快捷键: {config['hotkey']['screenshot']}")
        logging.info("划词读取功能已激活。")
        logging.info("按 Ctrl+C 退出程序。")

        # 保持主线程活动以响应Ctrl+C
        while not shutdown_event.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                logging.info("接收到退出信号 (Ctrl+C)，正在关闭服务...")
                shutdown_event.set()
                break

    except Exception as e:
        logging.critical(f"程序启动时发生致命错误: {e}", exc_info=True)
        shutdown_event.set()
    finally:
        logging.info("正在等待所有服务线程停止...")
        # 等待所有非守护线程完成
        for thread in threads:
            if thread.is_alive() and not thread.daemon:
                thread.join(timeout=3.0)
        logging.info("服务已关闭。")

if __name__ == "__main__":
    main()

