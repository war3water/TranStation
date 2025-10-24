import logging
import sys

def setup_logging():
    """
    配置全局日志记录器。
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(threadName)-25.25s] [%(levelname)-5.5s]  %(message)s",
        stream=sys.stdout
    )