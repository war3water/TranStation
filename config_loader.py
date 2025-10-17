import yaml
import logging
import sys

def load_config(config_path='config.yaml'):
    """
    加载 YAML 配置文件。
    :param config_path: 配置文件的路径。
    :return: 包含配置项的字典。
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            logging.info(f"配置文件 '{config_path}' 加载成功。")
            return config
    except FileNotFoundError:
        logging.error(f"错误：配置文件 '{config_path}' 未找到。")
        sys.exit(1) # 退出程序
    except yaml.YAMLError as e:
        logging.error(f"错误：解析配置文件 '{config_path}' 时出错: {e}")
        sys.exit(1) # 退出程序
