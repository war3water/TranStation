import logging
import logging.handlers
import os

def setup_logging():
    """
    配置应用程序的日志记录。
    - DEBUG 级别及以上的日志会写入到文件 `app.log` 中。
    - INFO 级别及以上的日志会输出到控制台。
    """
    log_formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(threadName)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 设置最低级别为 DEBUG

    # --- 文件处理器 ---
    # 创建 logs 目录（如果不存在）
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 使用 RotatingFileHandler，当日志文件达到 1MB 时会自动轮换，最多保留 5 个备份
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/app.log', maxBytes=1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    # --- 控制台处理器 ---
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    logging.info("日志系统初始化完成。")
