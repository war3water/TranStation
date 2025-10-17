# src/config_loader.py
import yaml
import os
from typing import Dict, Any

class ConfigLoader:
    """
    一个单例类，用于加载、解析和提供对 `config.yaml` 的访问。
    """
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """
        加载并解析 YAML 配置文件。
        """
        config_path = self._find_config_path()
        if not config_path:
            raise FileNotFoundError("config.yaml not found in project root.")

        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)

    def _find_config_path(self) -> str | None:
        """
        从当前工作目录向上查找 config.yaml 文件。
        """
        # 通常脚本在项目根目录运行
        if os.path.exists("config.yaml"):
            return "config.yaml"
        # 兼容从其他目录运行测试等情况
        path = os.getcwd()
        for _ in range(4): # 向上查找最多4层
            if "config.yaml" in os.listdir(path):
                return os.path.join(path, "config.yaml")
            path = os.path.dirname(path)
        return None


    def get_config(self) -> Dict[str, Any]:
        """
        返回已加载的配置字典。
        """
        if self._config is None:
            self._load_config()
        return self._config

    def get_property(self, property_path: str) -> Any:
        """
        使用点表示法获取嵌套的配置属性。
        例如: "server.host"
        """
        keys = property_path.split('.')
        value = self.get_config()
        for key in keys:
            value = value.get(key)
            if value is None:
                return None
        return value
